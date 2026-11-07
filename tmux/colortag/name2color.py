#!/usr/bin/env python
import argparse
import os
import sys
import errno
import hashlib
import pickle


def warn(msg):
    sys.stderr.write(msg + '\n')


def error(msg):
    print("ColorTag: {}\n".format(msg))


# add your favorite color code (256) here as candidates
# Catppuccin Mocha accents
colors = ['#f38ba8', '#a6e3a1', '#f9e2af', '#89b4fa', '#f5c2e7', '#94e2d5', '#fab387', '#cba6f7']
#         red        green      yellow     blue       pink       teal       peach      mauve
BASE = '#1e1e2e'  # Catppuccin Mocha base: the bar color that --alpha blends into

parser = argparse.ArgumentParser(description='Maps tmux window tags to colors.')
parser.add_argument('session', type=str, help='session name')
parser.add_argument('idx', type=int, help='index of the window')
parser.add_argument('name', type=str, help='name of the window')
parser.add_argument('--color-idx', type=int, help='manually change the color mapping for an index')
parser.add_argument('--color-name', type=int, help='manually change the color mapping for a name')
parser.add_argument('--clear-idx', action='store_true')
parser.add_argument('--clear-name', action='store_true')
parser.add_argument('--clear', action='store_true')
parser.add_argument('--show-state', action='store_true')
parser.add_argument('--alpha', type=float, help='print the color blended into the bar (colour237) at this strength, as #rrggbb')
parser.add_argument('--cycle', type=int, nargs='?', const=1, help='move this window to the next (1) or previous (-1) palette color')
args = parser.parse_args()

xdg_config_home_path = os.environ.get("XDG_CONFIG_HOME")
tmux_plugin_manager_path = os.environ.get("TMUX_PLUGIN_MANAGER_PATH") or ""
if xdg_config_home_path is None:
    xdg_config_home_path = ""
else:
    xdg_config_home_path = os.path.join(xdg_config_home_path, "tmux/plugins")

try_plugin_paths = [os.path.expanduser(path) for path in [
    xdg_config_home_path,
    tmux_plugin_manager_path,
]]

tmux_plugins_path = None
for plugin_path in try_plugin_paths:
    if os.path.exists(plugin_path):
        tmux_plugins_path = plugin_path
        break

if tmux_plugins_path is None:
    tmux_plugins_path = os.path.expanduser("~/.tmux/plugins")

state_prefix = os.path.join(tmux_plugins_path, "tmux-colortag/state")

state = {}
changed = True

try:
    os.makedirs(state_prefix)
except OSError as e:
    if e.errno != errno.EEXIST:
        raise
saved_state = os.path.join(
    state_prefix,
    "{}.state".format(args.session))

try:
    with open(saved_state, "rb") as f:
        _state = pickle.load(f)
        if type(_state) is dict:
            state = _state
            changed = False
except Exception:
    pass

if args.clear:
    state = {}
    changed = True

if len(args.name) > 100:
    error("invalid name")
if args.idx < 0 or args.idx >= 1024:
    error("invalid idx")

if args.show_state:
    print("ColorTag: manual coloring for session \"{}\"".format(args.session))
    for (k, v) in state.items():
        print("{} => colour{}".format(k, v))
    sys.exit(0)

if args.clear_idx:
    try:
        del state[args.idx]
    except Exception:
        pass
    changed = True

if args.clear_name:
    try:
        del state[args.name]
    except Exception:
        pass
    changed = True

if not (args.color_idx is None):
    if args.color_idx < 0 or args.color_idx >= 256:
        error("invalid color code")
        sys.exit(0)
    state[args.idx] = args.color_idx
    changed = True

if not (args.color_name is None):
    if args.color_name < 0 or args.color_name >= 256:
        error("invalid color code")
        sys.exit(0)
    state[args.name] = args.color_name
    changed = True

def default_color():
    # each session starts at its own palette color (stable hash of the session
    # name), then windows step through the palette by index
    offset = int(hashlib.sha1(args.session.encode('utf-8')).hexdigest(), 16)
    return colors[(args.idx + offset) % len(colors)]


if args.cycle:
    cur = state.get(args.idx, state.get(args.name, default_color()))
    i = colors.index(cur) if cur in colors else 0
    state[args.idx] = colors[(i + args.cycle) % len(colors)]
    changed = True

if changed:
    warn("wrote to the state")
    try:
        with open(saved_state, "wb") as f:
            pickle.dump(state, f)
    except Exception:
        warn("failed to dump file")
    sys.exit(0)

c = state.get(args.idx, None)
if c is None:
    c = state.get(args.name, None)
if c is None:
    # color by window index (offset per session) so neighbouring windows differ
    c = default_color()

def to_rgb(c):
    # a palette hex string, or a 0-255 code from a manual color-idx/color-name pin
    if isinstance(c, str):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    if c < 16:
        return (128, 128, 128)
    if c >= 232:
        v = 8 + (c - 232) * 10
        return (v, v, v)
    c -= 16
    lv = [0, 95, 135, 175, 215, 255]
    return (lv[c // 36], lv[(c // 6) % 6], lv[c % 6])


if args.alpha is not None:
    fg, bg = to_rgb(c), to_rgb(BASE)
    a = max(0.0, min(1.0, args.alpha))
    print("#{:02x}{:02x}{:02x}".format(*[round(f * a + b * (1 - a)) for f, b in zip(fg, bg)]))
elif isinstance(c, str):
    print(c)
else:
    print("colour{}".format(c))
