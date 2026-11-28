The chat form of an item in a release of format 2.0 or lower; in format 2.1 the item is its file, [queue-item.md](queue-item.md).

# Item template

## Default

```Markdown
# Q<n>. <One plain sentence.>
- <fact, or other line the decision needs>
  - <detail: code name, value>              optional
## Options:
1. Recommended: <the proposal in a few words>
   - <bullet>
     - <detail>                             optional
2..N. <another option>                      optional
   - <bullet>

**Say:**
- A. `record it`: record.
- B. `iterate`: record and start now.
```

## Example: when it is relevant to show the current behavior

```Markdown
# Q<n>. <One plain sentence.>
- Now                                       optional
  - <bullet>
    - <detail: code name, value>            optional
- <bullet>                                  optional
## Options:
1. Recommended: <the proposal in a few words>
   - <the thing that changes: the change>
     - <detail>                             optional
2..N. <another option>                      optional
   - <bullet>

**Say:**
- A. `record it`: record.
- B. `iterate`: record and start now.
```
