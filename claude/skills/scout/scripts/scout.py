#!/usr/bin/env python3
"""Scout fresh tools, repos, apps and libraries for a topic across many feeds at once.

Usage:
  python3 scout.py "<keywords>" [--days 30] [--top 15] [--feed URL ...] [--only a,b] [--json]

Sources live in ../sources.json (schema documented in its "_schema" block).
Stdlib only. Every source runs in parallel; a failed or slow source is skipped with one
stderr line "skipped: <name> (<reason>)" and never fails the run.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import email.utils
import html
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib

# Timing constants. The whole run should finish in about 8 s so the caller (an agent
# answering a chat request) stays fast.
REQUEST_TIMEOUT = 6.0   # per HTTP request (socket timeout). Healthy sources answer in 0.2-2.5 s.
RUN_DEADLINE = 7.5      # hard wall-clock cap for all sources; stragglers are reported as skipped.
GH_TOKEN_TIMEOUT = 2.0  # `gh auth token` fallback; never worth waiting longer.
MAX_BYTES = 2_000_000   # cap on a single response body (trending HTML is ~600 KB).

# Ranking constants.
HALF_LIFE_DAYS = 14.0   # recency decay: an item 14 days old counts half as much as one from today.
UNDATED_DECAY = 0.5     # decay used when a source gives no date (equal to a 14-day-old item).
NO_SCORE = 0.5          # normalized score for sources without a popularity signal.
MAX_SOURCE_SHARE = 0.4  # no single source may take more than 40% of the top N.
REL_FLOOR = 0.3         # rank weight = REL_FLOOR + (1 - REL_FLOOR) * fraction of keywords matched.
LOCAL_MIN_REL = 0.5     # local-filter sources with 3+ keywords keep items matching half of them.

# npm (type npm_search). The search API "date" is the LATEST publish, so famous old packages
# look fresh. Each candidate's FIRST publish date (packument time.created) is fetched instead,
# and only packages created within --days are kept.
NPM_CREATED_MAX = 20            # candidates checked per run (latest publish within --days, likeliest-new first).
NPM_CREATED_TIMEOUT = 3.0       # wall-clock cap per packument read; slower packages are dropped.
NPM_CREATED_MAX_BYTES = 4_000_000  # gzip bytes read per packument before giving up (react is ~1.3 MB).
NPM_DEADLINE_MARGIN = 0.4       # npm stops this long before RUN_DEADLINE so it never delays the run.
NPM_DL_FLOOR = 0.6              # weekly downloads only scale npm rank between 0.6 and 1.0;
                                #   creation recency (HALF_LIFE_DAYS decay) is the main signal.

# Cracked-software and malware bait that shows up on GitHub search and trending.
JUNK = re.compile(r"pre-?activated|\bcrack(ed)?\b|keygen|activator|license key|full version free",
                  re.I)
DESC_LEN = 100

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# Words dropped from local keyword matching: they match nearly everything in a feed.
STOPWORDS = {"a", "an", "the", "for", "of", "and", "or", "to", "in", "on", "with", "new", "cool",
             "best", "top", "good", "app", "apps", "tool", "tools", "open", "source", "free",
             "trending", "alternative", "alternatives", "library", "libraries", "project",
             "projects", "software", "this", "month", "week"}

NOW = time.time()


# ---------------------------------------------------------------- helpers

def log_skip(name, reason):
    print(f"skipped: {name} ({reason})", file=sys.stderr)


def describe_error(e):
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code}"
    if isinstance(e, urllib.error.URLError):
        return f"network: {e.reason}"[:80]
    if isinstance(e, (TimeoutError, OSError)):
        return f"timeout/network: {e}"[:80]
    if isinstance(e, ET.ParseError):
        return "not a valid feed (HTML or bad XML)"
    if isinstance(e, json.JSONDecodeError):
        return "not valid JSON"
    return f"{type(e).__name__}: {e}"[:80]


def fetch(url, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.8"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
        return r.read(MAX_BYTES)


def clean_text(s):
    if not s:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s*submitted by\s+/u/\S+.*$", "", s, flags=re.S)   # reddit footer
    s = re.sub(r"\s*Discussion\s*\|\s*Link\s*$", "", s)                 # product hunt footer
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_date(v):
    """Return unix seconds or None. Accepts epoch numbers, ISO 8601, RFC 822."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v / 1000 if v > 1e11 else v)
    s = str(v).strip()
    if s.isdigit():
        return parse_date(int(s))
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.timestamp()
    except ValueError:
        pass
    try:
        return email.utils.parsedate_to_datetime(s).timestamp()
    except (TypeError, ValueError):
        return None


def get_path(obj, path):
    if path in ("", None):
        return obj
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list) and part.isdigit() and int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return None
    return obj


def get_field(item, spec):
    """spec: dotted path, template with {path}, or list of those (first non-empty wins)."""
    if spec is None:
        return None
    if isinstance(spec, list):
        for s in spec:
            v = get_field(item, s)
            if v not in (None, "", []):
                return v
        return None
    if "{" in spec:
        missing = []

        def rep(m):
            val = get_path(item, m.group(1))
            if val in (None, ""):
                missing.append(m.group(1))
                return ""
            return str(val)
        out = re.sub(r"\{([^}]+)\}", rep, spec)
        return None if missing else out
    return get_path(item, spec)


def norm_url(u):
    try:
        p = urllib.parse.urlsplit(u.strip())
    except ValueError:
        return u
    host = p.netloc.lower().removeprefix("www.")
    path = p.path.rstrip("/")
    if host == "github.com":
        path = path.lower()
    return f"{host}{path}"


def make_item(source, title, url, desc="", score=None, date=None, tags=None):
    if isinstance(tags, str):
        tags = tags.split()
    return {
        "source": source,
        "title": clean_text(title),
        "url": (url or "").strip(),
        "desc": clean_text(desc),
        "score": float(score) if isinstance(score, (int, float)) else None,
        "date": parse_date(date),
        "tags": [str(t) for t in (tags or []) if isinstance(t, (str, int))],
    }


# ---------------------------------------------------------------- parsers

def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _child(el, *names):
    """First child matching any name, in name order. (Never use `or` on Elements: an
    Element without children is falsy.)"""
    for name in names:
        for c in el:
            if _local(c.tag) == name:
                return c
    return None


def parse_xml_feed(body, name):
    root = ET.fromstring(body)
    items = []
    if _local(root.tag) == "feed":                       # Atom
        for e in root:
            if _local(e.tag) != "entry":
                continue
            link = ""
            for c in e:
                if _local(c.tag) == "link" and c.get("rel", "alternate") == "alternate":
                    link = c.get("href", "")
                    break
            desc_el = _child(e, "summary", "content")
            date_el = _child(e, "published", "updated")
            title_el = _child(e, "title")
            tags = [c.get("term", "") for c in e if _local(c.tag) == "category"]
            items.append(make_item(name, title_el.text if title_el is not None else "", link,
                                   desc_el.text if desc_el is not None else "",
                                   None, date_el.text if date_el is not None else None, tags))
    else:                                               # RSS 2.0 / RDF
        for e in root.iter():
            if _local(e.tag) != "item":
                continue
            def g(*n):
                c = _child(e, *n)
                return c.text if c is not None else None
            tags = [c.text or "" for c in e if _local(c.tag) == "category"]
            items.append(make_item(name, g("title"), g("link"), g("description"), None,
                                   g("pubDate", "date", "updated"), tags))
    return items


def parse_json_feed(body, src):
    data = json.loads(body)
    lst = get_path(data, src.get("items", ""))
    if not isinstance(lst, list):
        raise ValueError("item path not a list")
    f = src.get("fields", {})
    out = []
    for it in lst:
        if not isinstance(it, dict):
            continue
        out.append(make_item(src["name"], get_field(it, f.get("title")), get_field(it, f.get("url")),
                             get_field(it, f.get("desc")), get_field(it, f.get("score")),
                             get_field(it, f.get("date")), get_field(it, f.get("tags"))))
    return out


def autodetect(body, name):
    """For --feed: JSON (list or common wrapper keys) or RSS/Atom."""
    text = body.lstrip()
    if text[:1] in (b"{", b"["):
        data = json.loads(body)
        if isinstance(data, dict):
            for k in ("items", "hits", "articles", "results", "data", "entries", "posts"):
                if isinstance(data.get(k), list):
                    data = data[k]
                    break
        if not isinstance(data, list):
            raise ValueError("no item list in JSON")
        src = {"name": name, "items": "", "fields": {
            "title": ["title", "name", "full_name"],
            "url": ["url", "html_url", "link", "href"],
            "desc": ["description", "summary", "tagline", "text"],
            "score": ["score", "points", "stars", "stargazers_count", "votes", "likes"],
            "date": ["published_at", "created_at", "date", "updated_at", "published", "createdAt"],
            "tags": ["tags", "topics"]}}
        return parse_json_feed(body, src)
    return parse_xml_feed(body, name)


_TREND_ARTICLE = re.compile(r'<article class="Box-row">(.*?)</article>', re.S)
_TREND_REPO = re.compile(r'<h2[^>]*>\s*<a[^>]*href="/([^"/]+/[^"/]+)"', re.S)
_TREND_DESC = re.compile(r'<p class="col-9[^"]*">(.*?)</p>', re.S)
_TREND_STARS = re.compile(r'([\d,]+)\s+stars\s+(?:this|today)', re.S)
_TREND_LANG = re.compile(r'itemprop="programmingLanguage">([^<]+)<')


def parse_trending(body, name):
    text = body.decode("utf-8", "replace")
    items = []
    for block in _TREND_ARTICLE.findall(text):
        m = _TREND_REPO.search(block)
        if not m:
            continue
        repo = m.group(1)
        d = _TREND_DESC.search(block)
        s = _TREND_STARS.search(block)
        lang = _TREND_LANG.search(block)
        items.append(make_item(name, repo, f"https://github.com/{repo}",
                               d.group(1) if d else "",
                               int(s.group(1).replace(",", "")) if s else None,
                               None, [lang.group(1)] if lang else []))
    if not items:
        raise ValueError("trending markup changed (0 repos parsed)")
    return items


# ---------------------------------------------------------------- github

def github_token():
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                           timeout=GH_TOKEN_TIMEOUT)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def run_github_search(src, ctx):
    headers = {"Accept": "application/vnd.github+json"}
    if ctx["gh_token"]:
        headers["Authorization"] = f"Bearer {ctx['gh_token']}"

    def query(words):
        url = fill(src["url"], ctx, q=urllib.parse.quote_plus(" ".join(words)))
        data = json.loads(fetch(url, headers))
        return data.get("items", [])

    words = ctx["keywords"]
    items = query(words)
    # GitHub ANDs every word; a long phrase often yields nothing. Retry with the two most
    # specific (longest) words.
    if not items and len(words) > 2:
        items = query(sorted(words, key=len, reverse=True)[:2])
    return [make_item(src["name"], it.get("full_name"), it.get("html_url"), it.get("description"),
                      it.get("stargazers_count"), it.get("created_at"), it.get("topics"))
            for it in items]


# ---------------------------------------------------------------- npm

_NPM_CREATED = re.compile(rb'"created"\s*:\s*"([^"]+)"')


def npm_created(name, deadline):
    """First publish time (unix s) of an npm package, or None. Streams the gzip packument and
    stops at "created" (the "time" block sits after "versions", so most of it is read)."""
    end = min(time.time() + NPM_CREATED_TIMEOUT, deadline)
    url = "https://registry.npmjs.org/" + urllib.parse.quote(name, safe="@")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=max(0.2, end - time.time())) as r:
        dec = zlib.decompressobj(31) if r.headers.get("Content-Encoding") == "gzip" else None
        tail, raw = b"", 0
        while time.time() < end and raw < NPM_CREATED_MAX_BYTES:
            chunk = r.read(65536)
            if not chunk:
                return None
            raw += len(chunk)
            buf = tail + (dec.decompress(chunk) if dec else chunk)
            m = _NPM_CREATED.search(buf)
            if m:
                return parse_date(m.group(1).decode())
            tail = buf[-200:]
    return None


def run_npm_search(src, ctx):
    """npm search gives candidates; keep only packages FIRST published within --days."""
    body = fetch(fill(src["url"], ctx))
    raw = [o for o in (get_path(json.loads(body), src.get("items", "")) or []) if isinstance(o, dict)]
    items = parse_json_feed(body, src)          # same order and length as raw
    # Latest publish older than the window means first publish is too: skip without a fetch.
    pairs = [(o, i) for o, i in zip(raw, items) if i["date"] and i["date"] >= ctx["since_ts"]]
    # Search ranks by popularity, so new packages sit deep in the list. Check the likeliest
    # new ones first, interleaving two cheap hints from the search result:
    #   a) no dependents, 0.x version, fewest weekly downloads;
    #   b) lowest monthly/weekly download ratio (an old package sits near 4.3, a new one near 1).
    def dl(o, k):
        return get_path(o, f"downloads.{k}") or 0

    def hint_a(p):
        o = p[0]
        major = str(get_path(o, "package.version") or "0").split(".")[0]
        return (str(o.get("dependents") or "0") != "0", major != "0", dl(o, "weekly"))

    def hint_b(p):
        o = p[0]
        w = dl(o, "weekly")
        return (dl(o, "monthly") / w if w else 99, w)

    order, seen = [], set()
    for pa, pb in zip(sorted(pairs, key=hint_a), sorted(pairs, key=hint_b)):
        for _, i in (pa, pb):
            if i["title"] not in seen:
                seen.add(i["title"])
                order.append(i)
    items = order[:NPM_CREATED_MAX]
    deadline = ctx["t0"] + RUN_DEADLINE - NPM_DEADLINE_MARGIN
    if not items or time.time() >= deadline:
        return []
    ex = cf.ThreadPoolExecutor(max_workers=len(items))
    futs = {ex.submit(npm_created, i["title"], deadline): i for i in items}
    kept = []
    try:
        for f in cf.as_completed(futs, timeout=max(0.1, deadline - time.time())):
            try:
                created = f.result()
            except Exception:
                continue        # unreachable packument: drop the package
            if created and created >= ctx["since_ts"]:
                i = futs[f]
                i["date"], i["created"], i["norm_floor"] = created, True, NPM_DL_FLOOR
                kept.append(i)
    except cf.TimeoutError:
        pass                    # packages still loading at the deadline are dropped
    ex.shutdown(wait=False, cancel_futures=True)
    return kept


# ---------------------------------------------------------------- engine

def fill(template, ctx, q=None):
    return (template.replace("{q}", q if q is not None else ctx["q"])
            .replace("{tag}", ctx["tag"])
            .replace("{since_date}", ctx["since_date"])
            .replace("{since_ts}", str(ctx["since_ts"])))


def relevance(item, terms):
    """Fraction of keyword terms found (word-start match) in title/desc/tags/url."""
    hay = " ".join([item["title"], item["desc"], " ".join(item["tags"]), item["url"]]).lower()
    # "self-hosted" also matches "self hosted" and "selfhosted".
    pats = [r"[-\s]?".join(re.escape(p) for p in t.split("-")) for t in terms]
    hits = sum(1 for p in pats if re.search(r"(?<![a-z0-9])" + p, hay))
    return hits / len(terms)


def run_source(src, ctx):
    t = src.get("type", "rss")
    if t == "github_search":
        items = run_github_search(src, ctx)
    elif t == "npm_search":
        items = run_npm_search(src, ctx)
    else:
        body = fetch(fill(src["url"], ctx, q=ctx["q"]))
        if t == "github_trending":
            items = parse_trending(body, src["name"])
        elif t == "json":
            items = parse_json_feed(body, src)
        elif t in ("rss", "atom"):
            items = parse_xml_feed(body, src["name"])
        elif t == "auto":
            items = autodetect(body, src["name"])
        else:
            raise ValueError(f"unknown type {t}")
    for i in items:
        i["rel"] = relevance(i, ctx["terms"])
        i["weight"] = float(src.get("weight", 1.0))
    if "min_rel" in src:
        need = float(src["min_rel"])
    elif src.get("keyword", "local") == "local":
        # General feeds (trending, launches) need a strict match or they flood the list:
        # all terms for 1-2 keywords, at least LOCAL_MIN_REL of them for 3+.
        need = 1.0 if len(ctx["terms"]) <= 2 else LOCAL_MIN_REL
    else:
        # Server search can match hidden text (comments, READMEs); with no keyword in
        # the visible title/desc/tags the hit is usually noise.
        need = 1e-6
    items = [i for i in items if i["rel"] >= need - 1e-9]
    items = [i for i in items if not JUNK.search(i["title"] + " " + i["desc"])]
    if src.get("undated") == "now":
        for i in items:
            i["date"] = i["date"] or NOW
    for i in items:
        i["unit"] = src.get("unit", "")
    return [i for i in items if i["title"] and i["url"].startswith("http")]


def topic_ok(src, ctx):
    topics = src.get("topics")
    if not topics:
        return True
    words = set(re.split(r"[\s\-_/]+", " ".join(ctx["keywords"]).lower()))
    return bool(words & {w.lower() for w in topics})


def rank(items, days, top):
    cutoff = NOW - days * 86400
    items = [i for i in items if i["date"] is None or i["date"] >= cutoff]
    # Normalize score per source on a log scale (popularity is heavy-tailed).
    by_src = {}
    for i in items:
        by_src.setdefault(i["source"], []).append(i)
    for lst in by_src.values():
        mx = max((i["score"] or 0) for i in lst)
        for i in lst:
            if i["score"] is None or mx <= 0:
                i["norm"] = NO_SCORE
            else:
                i["norm"] = math.log1p(max(i["score"], 0)) / math.log1p(mx)
            floor = i.get("norm_floor", 0.0)
            i["norm"] = floor + (1 - floor) * i["norm"]
    for i in items:
        if i["date"] is None:
            decay = UNDATED_DECAY
        else:
            age = max(0.0, (NOW - i["date"]) / 86400)
            decay = 0.5 ** (age / HALF_LIFE_DAYS)
        # Relevance weight: items matching every keyword beat items matching one.
        weight = REL_FLOOR + (1 - REL_FLOOR) * i.get("rel", 1.0)
        i["rank"] = max(i["norm"], 0.05) * decay * weight * i.get("weight", 1.0)
    # Dedupe by normalized URL, keep best, remember other sources.
    best = {}
    for i in sorted(items, key=lambda x: x["rank"], reverse=True):
        k = norm_url(i["url"])
        if k in best:
            if i["source"] != best[k]["source"] and i["source"] not in best[k]["also"]:
                best[k]["also"].append(i["source"])
            continue
        i["also"] = []
        best[k] = i
    ordered = list(best.values())
    # Source diversity: cap each source at MAX_SOURCE_SHARE of top N, then backfill.
    cap = max(2, math.ceil(top * MAX_SOURCE_SHARE))
    picked, rest, count = [], [], {}
    for i in ordered:
        if len(picked) < top and count.get(i["source"], 0) < cap:
            picked.append(i)
            count[i["source"]] = count.get(i["source"], 0) + 1
        else:
            rest.append(i)
    picked += rest[: max(0, top - len(picked))]
    return picked, len(ordered)


def compact(n):
    n = float(n)
    for div, suf in ((1e6, "M"), (1e3, "k")):
        if n >= div:
            return f"{n / div:.1f}".rstrip("0").rstrip(".") + suf
    return str(int(n))


def signal(i):
    if i.get("created"):       # npm: age is since FIRST publish
        age = int((NOW - i["date"]) / 86400)
        return f"new {age}d, {compact(i['score'] or 0)}{i.get('unit', '')}"
    parts = []
    if i["score"] is not None:
        parts.append(f"{int(i['score'])}{i.get('unit', '')}")
    if i["date"]:
        age = (NOW - i["date"]) / 86400
        parts.append("today" if age < 1 else f"{int(age)}d")
    return " ".join(parts) or "-"


def main():
    ap = argparse.ArgumentParser(description="Find fresh tools/repos/apps for a topic.")
    ap.add_argument("keywords")
    ap.add_argument("--days", type=int, default=30, help="drop dated items older than this")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--feed", action="append", default=[], help="extra rss/atom/json feed URL")
    ap.add_argument("--only", default="", help="comma list of source names to run")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    t0 = time.time()

    keywords = [w for w in re.split(r"\s+", a.keywords.strip()) if w]
    if not keywords:
        ap.error("keywords required")
    terms = [w.lower() for w in keywords if w.lower() not in STOPWORDS] or [keywords[0].lower()]
    tag = re.sub(r"[^a-z0-9]", "", terms[0])  # first keyword = most specific, by convention
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)
    ctx = {"keywords": keywords, "terms": terms, "tag": tag,
           "q": urllib.parse.quote_plus(" ".join(keywords)),
           "since_date": since.strftime("%Y-%m-%d"), "since_ts": int(since.timestamp()),
           "gh_token": None, "t0": t0}

    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sources.json")
    try:
        with open(cfg_path, encoding="utf-8") as fh:
            sources = [s for s in json.load(fh).get("sources", []) if s.get("enabled", True)]
    except (OSError, ValueError) as e:
        print(f"warning: cannot read sources.json ({e}); using --feed only", file=sys.stderr)
        sources = []
    if a.only:
        wanted = {n.strip() for n in a.only.split(",") if n.strip()}
        sources = [s for s in sources if s["name"] in wanted]
    sources = [s for s in sources if topic_ok(s, ctx)]
    for n, url in enumerate(a.feed, 1):
        host = urllib.parse.urlsplit(url).netloc.removeprefix("www.") or f"feed{n}"
        sources.append({"name": host, "type": "auto", "url": url, "keyword": "local"})
    if any(s.get("type") == "github_search" for s in sources):
        ctx["gh_token"] = github_token()

    all_items, hit, skipped = [], [], []
    ex = cf.ThreadPoolExecutor(max_workers=max(1, len(sources)))
    futs = {ex.submit(run_source, s, ctx): s["name"] for s in sources}
    remaining = max(0.5, RUN_DEADLINE - (time.time() - t0))
    try:
        for f in cf.as_completed(futs, timeout=remaining):
            name = futs[f]
            try:
                res = f.result()
                hit.append(name)
                all_items.extend(res)
            except Exception as e:  # any network/parse failure: skip this source only
                skipped.append(name)
                log_skip(name, describe_error(e))
    except cf.TimeoutError:
        for f, name in futs.items():
            if not f.done():
                skipped.append(name)
                log_skip(name, "deadline")
    ex.shutdown(wait=False, cancel_futures=True)

    top, uniq = rank(all_items, a.days, a.top)
    elapsed = time.time() - t0
    if a.json:
        out = {"keywords": a.keywords, "days": a.days, "elapsed_s": round(elapsed, 2),
               "sources_hit": sorted(hit), "sources_skipped": sorted(skipped),
               "candidates": uniq,
               "items": [{k: i[k] for k in ("source", "title", "desc", "url", "score", "unit")}
                         | {"date": dt.datetime.fromtimestamp(i["date"], dt.timezone.utc)
                            .strftime("%Y-%m-%d") if i["date"] else None,
                            "also": i["also"], "signal": signal(i)} for i in top]}
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"# scout \"{a.keywords}\" days={a.days} | sources hit {len(hit)}, "
              f"skipped {len(skipped)} | {len(top)} of {uniq} unique | {elapsed:.1f}s")
        for i in top:
            desc = i["desc"][:DESC_LEN] + ("..." if len(i["desc"]) > DESC_LEN else "")
            src = i["source"] + ("+" + "+".join(i["also"]) if i["also"] else "")
            print(f"[{src}] {i['title']} | {desc} | {signal(i)} | {i['url']}")
    sys.stdout.flush()
    sys.stderr.flush()
    # Straggler threads may still be blocked in a socket read; exit without joining them
    # so the deadline holds.
    os._exit(0)


if __name__ == "__main__":
    main()
