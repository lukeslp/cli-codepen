# codepen-prefill

Push local HTML, CSS, and JS straight to CodePen from the command line. No copy-paste, no manual setup — just point it at your files and a new pen opens in your browser, ready to go.

Works with separate files, a single combined HTML file, or an entire project folder. Zero dependencies beyond Python 3.8+.

## Install

```bash
pip install codepen-prefill
```

## Quick start

```bash
# Single HTML file — extracts inline CSS, JS, external resources, everything
codepen-prefill --single index.html

# Separate files
codepen-prefill --html body.html --css style.css --js app.js

# Scan a project folder
codepen-prefill --folder ./my-project
```

That's it. Your browser opens with a prefilled pen.

## What it does

Given your local web files, `codepen-prefill` builds a JSON payload for [CodePen's Prefill API](https://blog.codepen.io/documentation/prefill/) and submits it through your browser. The pen editor opens with your code already loaded.

When parsing a single HTML file, it losslessly extracts:
- Inline `<style>` blocks into the CSS panel
- Inline `<script>` blocks into the JS panel
- External `<link>` and `<script src>` URLs into CodePen's external resource fields
- `<head>` content (viewport meta, etc.)
- Classes on the `<html>` tag
- The `<title>` as the pen title

Nothing gets modified — your code goes into CodePen exactly as written.

## All the options

```bash
# Add metadata
codepen-prefill --single index.html --title "My Demo" --description "A thing I made"

# Private pen
codepen-prefill --single index.html --private

# Editor layout
codepen-prefill --single index.html --layout top

# Preprocessors (auto-detected from file extensions, or set manually)
codepen-prefill --html template.pug --css style.scss --js app.ts

# Add external libraries
codepen-prefill --single index.html \
  --css-external "https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css" \
  --js-external "https://cdn.jsdelivr.net/npm/lodash@4/lodash.min.js"

# CSS starter (normalize or reset)
codepen-prefill --single index.html --css-starter normalize

# Just see the JSON payload without opening anything
codepen-prefill --single index.html --dry-run

# Output raw JSON
codepen-prefill --single index.html --output json

# Generate a standalone HTML form you can host as a "Open in CodePen" button
codepen-prefill --folder ./demo --output form --outfile open-in-codepen.html
```

### Preprocessor auto-detection

| Extension | Preprocessor |
|-----------|-------------|
| `.pug` | Pug |
| `.md` | Markdown |
| `.scss` | SCSS |
| `.sass` | Sass |
| `.less` | Less |
| `.styl` | Stylus |
| `.ts` | TypeScript |
| `.tsx`, `.jsx` | Babel |
| `.coffee` | CoffeeScript |

## Use it as a library

```python
from codepen_prefill import prefill_from_folder, open_pen

# Build payload from a folder and open it
data = prefill_from_folder("./my-project", title="My Project")
open_pen(data)
```

```python
from codepen_prefill import prefill_from_strings, get_form_html

# Build from raw strings
data = prefill_from_strings(
    html="<h1>Hello</h1>",
    css="h1 { color: coral; }",
    js="console.log('hi');",
)

# Get embeddable form HTML
form = get_form_html(data)
```

### Library functions

| Function | What it does |
|----------|-------------|
| `prefill_from_html(path)` | Parse a single HTML file |
| `prefill_from_files(html=, css=, js=)` | Read separate files |
| `prefill_from_folder(path)` | Scan a directory |
| `prefill_from_strings(html=, css=, js=)` | Use raw strings |
| `open_pen(data)` | Open prefilled pen in browser |
| `get_form_html(data)` | Get the HTML form as a string |
| `get_batch_html(directory)` | Get a batch launcher page for a directory of HTML files |

All functions accept optional keyword arguments for metadata: `title`, `description`, `private`, `layout`, `css_external`, `js_external`, etc.

## Inbox workflow

Drop HTML files into `inbox/`, run `--batch`, and they get processed into a launcher page and moved to `sent/` so your inbox is clean for the next round.

```bash
# Process inbox/ → generate launcher → move files to sent/
codepen-prefill --batch

# Preview without moving files
codepen-prefill --batch --no-move

# Explicit directory (no move, works as before)
codepen-prefill --batch ./my-visualizations --outfile launcher.html
```

After running `--batch`:
- `datavis-to-codepen.html` — the launcher page (opens in browser automatically)
- `sent/2026-03-15_143022/` — timestamped directory with the processed HTML files
- `inbox/` — empty (non-HTML files are left in place)

## How it works

1. Reads your files and builds a JSON payload matching CodePen's API spec
2. Writes a temporary HTML page containing a form with the payload
3. Opens that page in your browser
4. The form auto-submits to `https://codepen.io/pen/define/`
5. CodePen opens the pen editor with your code loaded

## License

MIT
