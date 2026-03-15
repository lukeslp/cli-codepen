#!/usr/bin/env python3
"""
codepen-prefill: Push local HTML/CSS/JS to CodePen via the Prefill API.

Accepts individual files, a single combined HTML file, or a folder of assets.
Generates a self-submitting HTML form that POSTs to CodePen's prefill endpoint,
opening a new pen pre-filled with your code and metadata.

Author: Luke Steuber
License: MIT
"""

import argparse
import html as html_mod
import json
import os
import re
import shutil
import sys
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CODEPEN_ENDPOINT = "https://codepen.io/pen/define/"

VALID_HTML_PREPROCESSORS = ("none", "pug", "markdown")
VALID_CSS_PREPROCESSORS = ("none", "less", "scss", "sass", "stylus")
VALID_CSS_STARTERS = ("", "normalize", "reset")
VALID_CSS_PREFIXES = ("", "autoprefixer", "prefixfree")
VALID_JS_PREPROCESSORS = ("", "none", "coffeescript", "babel", "typescript", "vue")
VALID_LAYOUTS = ("", "left", "top", "right")

# ---------------------------------------------------------------------------
# HTML parser — extracts <style>, <script>, and body from a single HTML file
# ---------------------------------------------------------------------------


def parse_single_html(filepath: str) -> dict:
    """
    Parse a single .html file and losslessly extract its components.

    Strategy:
      1. Extract all <style> blocks → css
      2. Extract all <script> blocks (non-external) → js
      3. Extract external <link rel="stylesheet"> hrefs → css_external
      4. Extract external <script src="..."> srcs → js_external
      5. Extract <head> content (minus extracted elements) → head
      6. Extract <body> inner content (minus extracted elements) → html
      7. Extract classes on <html> tag → html_classes
      8. If no <body>/<head> structure, treat the remainder as html

    Returns a dict with keys matching the CodePen API fields.
    """
    raw = Path(filepath).read_text(encoding="utf-8")
    result = {}

    # ---- html_classes from <html> tag ----
    html_tag_match = re.search(r"<html[^>]*\bclass\s*=\s*[\"']([^\"']*)[\"']", raw, re.IGNORECASE)
    if html_tag_match:
        result["html_classes"] = html_tag_match.group(1)

    # ---- Extract <head> content ----
    head_match = re.search(r"<head[^>]*>(.*?)</head>", raw, re.DOTALL | re.IGNORECASE)
    head_content = head_match.group(1) if head_match else ""

    # ---- Extract <body> content ----
    body_match = re.search(r"<body[^>]*>(.*?)</body>", raw, re.DOTALL | re.IGNORECASE)
    if body_match:
        body_content = body_match.group(1)
    else:
        # No body tag — strip doctype, <html>, <head> and treat the rest as body
        body_content = raw
        body_content = re.sub(r"<!DOCTYPE[^>]*>", "", body_content, flags=re.IGNORECASE)
        body_content = re.sub(r"</?html[^>]*>", "", body_content, flags=re.IGNORECASE)
        if head_match:
            body_content = body_content.replace(head_match.group(0), "")

    # ---- Collect inline <style> blocks → css ----
    css_parts = []
    def _collect_style(m):
        css_parts.append(m.group(1))
        return ""
    body_content = re.sub(
        r"<style[^>]*>(.*?)</style>",
        _collect_style,
        body_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    head_content = re.sub(
        r"<style[^>]*>(.*?)</style>",
        _collect_style,
        head_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if css_parts:
        result["css"] = "\n\n".join(p.strip() for p in css_parts if p.strip())

    # ---- Collect inline <script> blocks (no src) → js ----
    js_parts = []
    def _collect_script(m):
        tag = m.group(0)
        # Skip external scripts (they have src="...")
        if re.search(r'\bsrc\s*=', tag, re.IGNORECASE):
            return tag  # leave in place, will be handled below
        js_parts.append(m.group(1))
        return ""
    body_content = re.sub(
        r"<script[^>]*>(.*?)</script>",
        _collect_script,
        body_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    head_content = re.sub(
        r"<script[^>]*>(.*?)</script>",
        _collect_script,
        head_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if js_parts:
        result["js"] = "\n\n".join(p.strip() for p in js_parts if p.strip())

    # ---- Collect external CSS (<link rel="stylesheet">) → css_external ----
    css_externals = []
    def _collect_css_ext(m):
        href = re.search(r'href\s*=\s*["\']([^"\']+)["\']', m.group(0), re.IGNORECASE)
        if href:
            css_externals.append(href.group(1))
        return ""
    head_content = re.sub(
        r'<link[^>]*rel\s*=\s*["\']stylesheet["\'][^>]*/?>',
        _collect_css_ext,
        head_content,
        flags=re.IGNORECASE,
    )
    # Also match <link href="..." rel="stylesheet"> (href before rel)
    head_content = re.sub(
        r'<link[^>]*href\s*=\s*["\'][^"\']+["\'][^>]*rel\s*=\s*["\']stylesheet["\'][^>]*/?>',
        _collect_css_ext,
        head_content,
        flags=re.IGNORECASE,
    )
    body_content = re.sub(
        r'<link[^>]*rel\s*=\s*["\']stylesheet["\'][^>]*/?>',
        _collect_css_ext,
        body_content,
        flags=re.IGNORECASE,
    )
    if css_externals:
        result["css_external"] = ";".join(css_externals)

    # ---- Collect external JS (<script src="...">) → js_external ----
    js_externals = []
    def _collect_js_ext(m):
        src = re.search(r'src\s*=\s*["\']([^"\']+)["\']', m.group(0), re.IGNORECASE)
        if src:
            js_externals.append(src.group(1))
        return ""
    head_content = re.sub(
        r'<script[^>]*\bsrc\s*=\s*["\'][^"\']+["\'][^>]*>.*?</script>',
        _collect_js_ext,
        head_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    body_content = re.sub(
        r'<script[^>]*\bsrc\s*=\s*["\'][^"\']+["\'][^>]*>.*?</script>',
        _collect_js_ext,
        body_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if js_externals:
        result["js_external"] = ";".join(js_externals)

    # ---- Remaining <head> content (meta, title, etc.) → head ----
    # Strip <title> since CodePen has its own title field
    title_match = re.search(r"<title[^>]*>(.*?)</title>", head_content, re.DOTALL | re.IGNORECASE)
    if title_match:
        # Use as default title if not already set
        result.setdefault("title", title_match.group(1).strip())
        head_content = head_content.replace(title_match.group(0), "")

    # Remove charset meta (CodePen handles this)
    head_content = re.sub(
        r'<meta[^>]*charset\s*=\s*["\']?[^"\'>\s]+["\']?[^>]*/?>',
        "",
        head_content,
        flags=re.IGNORECASE,
    )

    head_content = head_content.strip()
    if head_content:
        # Clean up excessive whitespace
        head_content = re.sub(r"\n{3,}", "\n\n", head_content)
        result["head"] = head_content.strip()

    # ---- Body content → html ----
    body_content = body_content.strip()
    if body_content:
        body_content = re.sub(r"\n{3,}", "\n\n", body_content)
        result["html"] = body_content

    return result


# ---------------------------------------------------------------------------
# Folder scanner — discovers HTML, CSS, JS files in a directory
# ---------------------------------------------------------------------------


def scan_folder(folder: str) -> dict:
    """
    Scan a folder for web assets and build a CodePen data dict.

    Looks for:
      - index.html / *.html  → parsed as single HTML (first found)
      - *.css                 → concatenated into css
      - *.js                  → concatenated into js

    If an HTML file is found, it is parsed with parse_single_html() first,
    then any additional standalone CSS/JS files are appended.
    """
    folder_path = Path(folder)
    if not folder_path.is_dir():
        raise FileNotFoundError(f"Not a directory: {folder}")

    result = {}

    # Find HTML file (prefer index.html)
    html_files = sorted(folder_path.glob("*.html"))
    index_html = [f for f in html_files if f.name.lower() == "index.html"]
    primary_html = index_html[0] if index_html else (html_files[0] if html_files else None)

    if primary_html:
        result = parse_single_html(str(primary_html))
        # Remove this file from further processing
        html_files = [f for f in html_files if f != primary_html]

    # Additional HTML files — append to html content
    for hf in html_files:
        extra = Path(hf).read_text(encoding="utf-8")
        existing = result.get("html", "")
        result["html"] = (existing + "\n\n<!-- " + hf.name + " -->\n" + extra).strip()

    # CSS files (skip if already inlined from HTML)
    css_files = sorted(folder_path.glob("*.css"))
    if css_files:
        css_content = []
        for cf in css_files:
            css_content.append(f"/* {cf.name} */\n" + cf.read_text(encoding="utf-8"))
        existing_css = result.get("css", "")
        combined = (existing_css + "\n\n" + "\n\n".join(css_content)).strip()
        result["css"] = combined

    # JS files (skip if already inlined from HTML)
    js_files = sorted(folder_path.glob("*.js"))
    if js_files:
        js_content = []
        for jf in js_files:
            js_content.append(f"// {jf.name}\n" + jf.read_text(encoding="utf-8"))
        existing_js = result.get("js", "")
        combined = (existing_js + "\n\n" + "\n\n".join(js_content)).strip()
        result["js"] = combined

    # Also look for common preprocessor files
    preprocessor_map = {
        "*.scss": ("css", "scss"),
        "*.sass": ("css", "sass"),
        "*.less": ("css", "less"),
        "*.styl": ("css", "stylus"),
        "*.ts": ("js", "typescript"),
        "*.tsx": ("js", "babel"),
        "*.jsx": ("js", "babel"),
        "*.coffee": ("js", "coffeescript"),
        "*.pug": ("html", "pug"),
    }
    for pattern, (field, preprocessor) in preprocessor_map.items():
        files = sorted(folder_path.glob(pattern))
        if files:
            content = "\n\n".join(f.read_text(encoding="utf-8") for f in files)
            existing = result.get(field, "")
            result[field] = (existing + "\n\n" + content).strip() if existing else content
            result[f"{field}_pre_processor"] = preprocessor

    return result


# ---------------------------------------------------------------------------
# Build the CodePen JSON payload
# ---------------------------------------------------------------------------


def build_payload(
    *,
    html_file: Optional[str] = None,
    css_file: Optional[str] = None,
    js_file: Optional[str] = None,
    folder: Optional[str] = None,
    single_html: Optional[str] = None,
    # Metadata overrides
    title: Optional[str] = None,
    description: Optional[str] = None,
    private: Optional[bool] = None,
    layout: Optional[str] = None,
    # Preprocessors
    html_pre_processor: Optional[str] = None,
    css_pre_processor: Optional[str] = None,
    css_starter: Optional[str] = None,
    css_prefix: Optional[str] = None,
    js_pre_processor: Optional[str] = None,
    # Extra
    html_classes: Optional[str] = None,
    head: Optional[str] = None,
    css_external: Optional[str] = None,
    js_external: Optional[str] = None,
) -> dict:
    """
    Build the JSON payload for CodePen's prefill API.

    Input modes (in priority order):
      1. --folder   : scan a directory for assets
      2. --single   : parse a single combined HTML file
      3. --html / --css / --js : individual file arguments

    CLI flags override any auto-detected values.
    """
    data = {}

    # --- Input mode selection ---
    if folder:
        data = scan_folder(folder)
    elif single_html:
        data = parse_single_html(single_html)
    else:
        # Individual files
        if html_file:
            data["html"] = Path(html_file).read_text(encoding="utf-8")
        if css_file:
            data["css"] = Path(css_file).read_text(encoding="utf-8")
        if js_file:
            data["js"] = Path(js_file).read_text(encoding="utf-8")

    # --- Apply overrides (CLI flags always win) ---
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if private is not None:
        data["private"] = private
    if layout:
        data["layout"] = layout
    if html_pre_processor:
        data["html_pre_processor"] = html_pre_processor
    if css_pre_processor:
        data["css_pre_processor"] = css_pre_processor
    if css_starter:
        data["css_starter"] = css_starter
    if css_prefix:
        data["css_prefix"] = css_prefix
    if js_pre_processor:
        data["js_pre_processor"] = js_pre_processor
    if html_classes is not None:
        data["html_classes"] = html_classes
    if head is not None:
        data["head"] = head
    if css_external is not None:
        # Merge with any auto-detected externals
        existing = data.get("css_external", "")
        if existing:
            data["css_external"] = existing + ";" + css_external
        else:
            data["css_external"] = css_external
    if js_external is not None:
        existing = data.get("js_external", "")
        if existing:
            data["js_external"] = existing + ";" + js_external
        else:
            data["js_external"] = js_external

    # --- Auto-detect preprocessors from file extensions ---
    if html_file and not data.get("html_pre_processor"):
        ext = Path(html_file).suffix.lower()
        ext_map = {".pug": "pug", ".md": "markdown", ".markdown": "markdown"}
        if ext in ext_map:
            data["html_pre_processor"] = ext_map[ext]

    if css_file and not data.get("css_pre_processor"):
        ext = Path(css_file).suffix.lower()
        ext_map = {".scss": "scss", ".sass": "sass", ".less": "less", ".styl": "stylus"}
        if ext in ext_map:
            data["css_pre_processor"] = ext_map[ext]

    if js_file and not data.get("js_pre_processor"):
        ext = Path(js_file).suffix.lower()
        ext_map = {
            ".ts": "typescript",
            ".tsx": "babel",
            ".jsx": "babel",
            ".coffee": "coffeescript",
        }
        if ext in ext_map:
            data["js_pre_processor"] = ext_map[ext]

    # --- Clean up empty values ---
    data = {k: v for k, v in data.items() if v is not None and v != ""}

    return data


# ---------------------------------------------------------------------------
# Generate the self-submitting HTML form
# ---------------------------------------------------------------------------


def generate_form_html(data: dict, autosubmit: bool = True) -> str:
    """
    Generate an HTML page containing a form that POSTs to CodePen's prefill
    endpoint. If autosubmit is True, the form submits itself on page load.
    """
    json_str = json.dumps(data, ensure_ascii=False)
    # Escape for safe embedding in an HTML attribute value
    escaped = html_mod.escape(json_str, quote=True)

    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        "  <title>Redirecting to CodePen...</title>",
        "  <style>",
        "    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;",
        "           display: flex; align-items: center; justify-content: center;",
        "           min-height: 100vh; margin: 0; background: #1e1f26; color: #c5c8c6; }",
        "    .container { text-align: center; }",
        "    .spinner { width: 40px; height: 40px; margin: 20px auto;",
        "               border: 4px solid rgba(255,255,255,0.1);",
        "               border-top-color: #47cf73; border-radius: 50%;",
        "               animation: spin 0.8s linear infinite; }",
        "    @keyframes spin { to { transform: rotate(360deg); } }",
        '    button { background: #47cf73; color: #000; border: none;',
        "            padding: 12px 32px; font-size: 16px; border-radius: 6px;",
        "            cursor: pointer; margin-top: 16px; font-weight: 600; }",
        "    button:hover { background: #3ab563; }",
        "    .meta { margin-top: 24px; font-size: 13px; opacity: 0.5; }",
        "  </style>",
        "</head>",
        "<body>",
        '  <div class="container">',
    ]

    if autosubmit:
        lines += [
            '    <div class="spinner"></div>',
            "    <p>Opening CodePen...</p>",
        ]

    lines += [
        f'    <form id="cp-form" action="{CODEPEN_ENDPOINT}" method="POST">',
        f'      <input type="hidden" name="data" value="{escaped}">',
    ]

    if not autosubmit:
        lines.append('      <button type="submit">Open in CodePen</button>')

    lines += [
        "    </form>",
    ]

    # Show summary
    summary_parts = []
    if data.get("title"):
        summary_parts.append(f"Title: {html_mod.escape(data['title'])}")
    if data.get("html"):
        summary_parts.append(f"HTML: {len(data['html'])} chars")
    if data.get("css"):
        summary_parts.append(f"CSS: {len(data['css'])} chars")
    if data.get("js"):
        summary_parts.append(f"JS: {len(data['js'])} chars")
    if data.get("css_external"):
        n = len(data["css_external"].split(";"))
        summary_parts.append(f"External CSS: {n} file(s)")
    if data.get("js_external"):
        n = len(data["js_external"].split(";"))
        summary_parts.append(f"External JS: {n} file(s)")

    if summary_parts:
        lines.append('    <div class="meta">' + " &middot; ".join(summary_parts) + "</div>")

    lines += [
        "  </div>",
    ]

    if autosubmit:
        lines += [
            "  <script>",
            '    document.getElementById("cp-form").submit();',
            "  </script>",
        ]

    lines += [
        "</body>",
        "</html>",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output modes
# ---------------------------------------------------------------------------


def output_json(data: dict, outfile: Optional[str] = None):
    """Print or write the raw JSON payload."""
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    if outfile:
        Path(outfile).write_text(json_str, encoding="utf-8")
        print(f"JSON payload written to: {outfile}")
    else:
        print(json_str)


def output_form(data: dict, outfile: Optional[str] = None, autosubmit: bool = True):
    """Write the HTML form to a file."""
    form_html = generate_form_html(data, autosubmit=autosubmit)
    if outfile:
        Path(outfile).write_text(form_html, encoding="utf-8")
        print(f"Form HTML written to: {outfile}")
    else:
        print(form_html)


def open_in_browser(data: dict):
    """Write a temp HTML file and open it in the default browser."""
    form_html = generate_form_html(data, autosubmit=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(form_html)
        tmppath = f.name
    print(f"Opening CodePen in browser... (temp file: {tmppath})")
    webbrowser.open("file://" + os.path.abspath(tmppath))


def ensure_dirs(inbox: Path, sent: Path):
    """Create inbox and sent directories if they don't exist."""
    inbox.mkdir(parents=True, exist_ok=True)
    sent.mkdir(parents=True, exist_ok=True)


def move_to_sent(filepaths: list, sent_dir: Path):
    """
    Move processed HTML files to sent/<YYYY-MM-DD_HHMMSS>/.
    Handles filename collisions with a counter suffix.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest = sent_dir / timestamp
    dest.mkdir(parents=True, exist_ok=True)

    for fpath in filepaths:
        src = Path(fpath)
        target = dest / src.name
        # Handle collisions
        if target.exists():
            stem, suffix = target.stem, target.suffix
            counter = 1
            while target.exists():
                target = dest / f"{stem}_{counter}{suffix}"
                counter += 1
        shutil.move(str(src), str(target))


def generate_batch_html(directory: str, return_manifest: bool = False):
    """
    Scan a directory for HTML files and generate a launcher page with
    one CodePen submit button per file. Each file is parsed with
    parse_single_html() and the payload is embedded in a form.

    If return_manifest is True, returns (html_string, processed_files_list)
    instead of just the string.
    """
    dir_path = Path(directory)
    html_files = sorted(f for f in dir_path.iterdir() if f.suffix.lower() == ".html")

    if not html_files:
        raise FileNotFoundError(f"No .html files found in: {directory}")

    cards = []
    success = 0
    errors = []
    processed = []

    for fpath in html_files:
        try:
            data = parse_single_html(str(fpath))
            title = data.get(
                "title",
                fpath.stem.replace("-", " ").replace("_", " ").title(),
            )
            data["title"] = title

            json_str = json.dumps(data, ensure_ascii=False)
            escaped = html_mod.escape(json_str, quote=True)

            meta_parts = []
            if data.get("html"):
                meta_parts.append(f"HTML: {len(data['html'])}")
            if data.get("css"):
                meta_parts.append(f"CSS: {len(data['css'])}")
            if data.get("js"):
                meta_parts.append(f"JS: {len(data['js'])}")
            meta = " &middot; ".join(meta_parts) if meta_parts else "empty"

            cards.append(
                f'    <div class="card" data-name="{html_mod.escape(title.lower())}">\n'
                f'      <div class="card-title">{html_mod.escape(title)}</div>\n'
                f'      <div class="card-meta">{meta}</div>\n'
                f'      <form action="{CODEPEN_ENDPOINT}" method="POST" target="_blank"'
                f' onsubmit="this.parentElement.classList.add(\'sent\')">\n'
                f'        <input type="hidden" name="data" value="{escaped}">\n'
                f'        <button type="submit">Open in CodePen</button>\n'
                f"      </form>\n"
                f"    </div>"
            )
            processed.append(fpath)
            success += 1
        except Exception as e:
            errors.append(f"{fpath.name}: {e}")

    dir_name = html_mod.escape(dir_path.name)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{dir_name} &rarr; CodePen</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0d1117; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 2rem; }}
    h1 {{ margin-bottom: 0.5rem; }}
    .count {{ color: #8b949e; margin-bottom: 2rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }}
    .card-title {{ padding: 12px 16px; font-size: 14px; font-weight: 500; border-bottom: 1px solid #30363d; }}
    .card-meta {{ padding: 8px 16px; font-size: 12px; color: #8b949e; }}
    .card form {{ padding: 8px 16px 12px; }}
    button {{ background: #238636; color: #fff; border: none; padding: 8px 16px; font-size: 13px; border-radius: 6px; cursor: pointer; width: 100%; font-weight: 500; }}
    button:hover {{ background: #2ea043; }}
    button:focus-visible {{ outline: 2px solid #58a6ff; outline-offset: 2px; }}
    .sent button {{ background: #30363d; color: #8b949e; }}
    .filter {{ margin-bottom: 1.5rem; }}
    .filter input {{ background: #0d1117; border: 1px solid #30363d; color: #e6edf3; padding: 8px 12px; border-radius: 6px; font-size: 14px; width: 100%; max-width: 400px; }}
    .filter input:focus {{ outline: none; border-color: #58a6ff; }}
  </style>
</head>
<body>
  <h1>{dir_name} &rarr; CodePen</h1>
  <p class="count">{success} visualizations ready to send</p>
  <div class="filter"><input type="text" id="search" placeholder="Filter..." oninput="filter(this.value)"></div>
  <div class="grid" id="grid">
{chr(10).join(cards)}
  </div>
  <script>
    function filter(q) {{
      q = q.toLowerCase();
      document.querySelectorAll(".card").forEach(c => {{
        c.style.display = c.dataset.name.includes(q) ? "" : "none";
      }});
    }}
  </script>
</body>
</html>"""

    if errors:
        for e in errors:
            print(f"  Warning: {e}", file=sys.stderr)

    if return_manifest:
        return page, processed
    return page


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codepen-prefill",
        description=(
            "Push local HTML/CSS/JS to CodePen via the Prefill API.\n\n"
            "Accepts individual files, a single combined HTML file, or a folder\n"
            "of assets. Generates a form that opens a prefilled pen in your browser."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:

  # Open a single HTML file in CodePen
  codepen-prefill --single index.html

  # Push separate files with a title
  codepen-prefill --html body.html --css style.css --js app.js --title "My Pen"

  # Scan a project folder
  codepen-prefill --folder ./my-project --title "Project Demo"

  # Export JSON payload instead of opening browser
  codepen-prefill --single index.html --output json

  # Save the form HTML to a file
  codepen-prefill --folder ./demo --output form --outfile codepen-form.html

  # Use preprocessors
  codepen-prefill --html template.pug --css style.scss --js app.ts

  # Add external libraries
  codepen-prefill --html index.html --css-external "https://cdn.example.com/lib.css" \\
                  --js-external "https://cdn.example.com/lib.js;https://cdn.example.com/plugin.js"

  # Private pen with layout preference
  codepen-prefill --single index.html --private --layout top

  # Batch mode — generate a launcher page for a directory of HTML files
  codepen-prefill --batch ./my-visualizations --outfile launcher.html

  # Inbox workflow — process inbox/, move files to sent/, open launcher
  codepen-prefill --batch

  # Preview inbox without moving files
  codepen-prefill --batch --no-move
        """,
    )

    # --- Input sources (mutually exclusive groups) ---
    input_group = parser.add_argument_group("Input Sources")
    input_group.add_argument(
        "--single", "-s",
        metavar="FILE",
        help="Single combined HTML file to parse and split into HTML/CSS/JS",
    )
    input_group.add_argument(
        "--folder", "-f",
        metavar="DIR",
        help="Folder of web assets to scan (looks for *.html, *.css, *.js, etc.)",
    )
    input_group.add_argument(
        "--html",
        metavar="FILE",
        help="HTML file (or Pug/Markdown with appropriate --html-pre-processor)",
    )
    input_group.add_argument(
        "--css",
        metavar="FILE",
        help="CSS file (or SCSS/SASS/Less/Stylus)",
    )
    input_group.add_argument(
        "--js",
        metavar="FILE",
        help="JavaScript file (or TypeScript/CoffeeScript/JSX)",
    )
    input_group.add_argument(
        "--batch", "-b",
        nargs="?",
        const="__inbox__",
        metavar="DIR",
        help="Batch mode: scan a directory of HTML files and generate a launcher page. "
             "Without a directory argument, processes inbox/ and moves files to sent/.",
    )
    input_group.add_argument(
        "--no-move",
        action="store_true",
        help="With --batch (inbox mode): generate launcher but don't move files to sent/",
    )

    # --- Metadata ---
    meta_group = parser.add_argument_group("Metadata")
    meta_group.add_argument("--title", "-t", help="Pen title")
    meta_group.add_argument("--description", "-d", help="Pen description")
    meta_group.add_argument(
        "--private", action="store_true", default=None,
        help="Save as private pen (if user has the privilege)",
    )
    meta_group.add_argument(
        "--layout",
        choices=["left", "top", "right"],
        help="Editor layout",
    )

    # --- Preprocessors ---
    pre_group = parser.add_argument_group("Preprocessors & Settings")
    pre_group.add_argument(
        "--html-pre-processor",
        choices=["none", "pug", "markdown"],
        help="HTML preprocessor",
    )
    pre_group.add_argument(
        "--css-pre-processor",
        choices=["none", "less", "scss", "sass", "stylus"],
        help="CSS preprocessor",
    )
    pre_group.add_argument(
        "--css-starter",
        choices=["normalize", "reset"],
        help="CSS starter (normalize or reset)",
    )
    pre_group.add_argument(
        "--css-prefix",
        choices=["autoprefixer", "prefixfree"],
        help="CSS vendor prefix method",
    )
    pre_group.add_argument(
        "--js-pre-processor",
        choices=["none", "coffeescript", "babel", "typescript", "vue"],
        help="JS preprocessor",
    )

    # --- Extra content ---
    extra_group = parser.add_argument_group("Extra Content")
    extra_group.add_argument(
        "--html-classes",
        help="Classes to add to the <html> element",
    )
    extra_group.add_argument(
        "--head",
        help='Extra content for <head> (e.g., \'<meta name="viewport" ...>\')',
    )
    extra_group.add_argument(
        "--head-file",
        metavar="FILE",
        help="File containing extra <head> content",
    )
    extra_group.add_argument(
        "--css-external",
        help="Semicolon-separated external CSS URLs",
    )
    extra_group.add_argument(
        "--js-external",
        help="Semicolon-separated external JS URLs",
    )

    # --- Output ---
    out_group = parser.add_argument_group("Output")
    out_group.add_argument(
        "--output", "-o",
        choices=["browser", "json", "form"],
        default="browser",
        help="Output mode: open in browser (default), print JSON, or generate form HTML",
    )
    out_group.add_argument(
        "--outfile",
        metavar="FILE",
        help="Write output to file instead of stdout (for json/form modes)",
    )
    out_group.add_argument(
        "--no-autosubmit",
        action="store_true",
        help="In form mode, don't auto-submit — show a button instead",
    )
    out_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be sent without opening browser or writing files",
    )

    return parser


def validate_file(path: str, label: str):
    """Validate that a file exists and is readable."""
    p = Path(path)
    if not p.exists():
        print(f"Error: {label} file not found: {path}", file=sys.stderr)
        sys.exit(1)
    if not p.is_file():
        print(f"Error: {label} path is not a file: {path}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = build_parser()
    args = parser.parse_args()

    # --- Batch mode (early exit) ---
    if args.batch is not None:
        inbox_dir = Path.cwd() / "inbox"
        sent_dir = Path.cwd() / "sent"
        use_inbox = args.batch == "__inbox__"

        if use_inbox:
            ensure_dirs(inbox_dir, sent_dir)
            batch_dir = inbox_dir
        else:
            batch_dir = Path(args.batch)
            # Check if explicit dir resolves to inbox/
            use_inbox = batch_dir.resolve() == inbox_dir.resolve()

        if not batch_dir.is_dir():
            print(f"Error: Batch directory not found: {batch_dir}", file=sys.stderr)
            sys.exit(1)

        if use_inbox and not args.no_move:
            page, processed = generate_batch_html(str(batch_dir), return_manifest=True)
        else:
            page = generate_batch_html(str(batch_dir))
            processed = []

        outfile = args.outfile or ("datavis-to-codepen.html" if use_inbox else None)
        if outfile:
            Path(outfile).write_text(page, encoding="utf-8")
            print(f"Batch launcher written to: {outfile}")
            webbrowser.open("file://" + os.path.abspath(outfile))
        else:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as f:
                f.write(page)
                tmppath = f.name
            print(f"Opening batch launcher in browser... (temp file: {tmppath})")
            webbrowser.open("file://" + os.path.abspath(tmppath))

        if use_inbox and not args.no_move and processed:
            move_to_sent(processed, sent_dir)
            print(f"Moved {len(processed)} file(s) to sent/")

        return

    # --- Validate inputs ---
    if not any([args.single, args.folder, args.html, args.css, args.js]):
        parser.print_help()
        print("\nError: No input provided. Use --single, --folder, or --html/--css/--js.", file=sys.stderr)
        sys.exit(1)

    if args.single and args.folder:
        print("Error: --single and --folder are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    if args.single and any([args.html, args.css, args.js]):
        print("Error: --single cannot be combined with --html/--css/--js.", file=sys.stderr)
        sys.exit(1)

    if args.folder and any([args.html, args.css, args.js]):
        print("Error: --folder cannot be combined with --html/--css/--js.", file=sys.stderr)
        sys.exit(1)

    # Validate file existence
    if args.single:
        validate_file(args.single, "Single HTML")
    if args.folder:
        if not Path(args.folder).is_dir():
            print(f"Error: Folder not found: {args.folder}", file=sys.stderr)
            sys.exit(1)
    if args.html:
        validate_file(args.html, "HTML")
    if args.css:
        validate_file(args.css, "CSS")
    if args.js:
        validate_file(args.js, "JS")
    if args.head_file:
        validate_file(args.head_file, "Head")

    # --- Resolve head content ---
    head_content = args.head
    if args.head_file:
        head_content = Path(args.head_file).read_text(encoding="utf-8")

    # --- Handle --private flag ---
    private_val = None
    if args.private:
        private_val = True

    # --- Build payload ---
    data = build_payload(
        html_file=args.html,
        css_file=args.css,
        js_file=args.js,
        folder=args.folder,
        single_html=args.single,
        title=args.title,
        description=args.description,
        private=private_val,
        layout=args.layout,
        html_pre_processor=args.html_pre_processor,
        css_pre_processor=args.css_pre_processor,
        css_starter=args.css_starter,
        css_prefix=args.css_prefix,
        js_pre_processor=args.js_pre_processor,
        html_classes=args.html_classes,
        head=head_content,
        css_external=args.css_external,
        js_external=args.js_external,
    )

    if not data:
        print("Warning: No content detected. The pen will be empty.", file=sys.stderr)

    # --- Dry run ---
    if args.dry_run:
        print("=== DRY RUN — Payload that would be sent ===\n")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"\nPayload size: {len(json.dumps(data, ensure_ascii=False))} bytes")
        if data.get("html"):
            print(f"HTML: {len(data['html'])} chars")
        if data.get("css"):
            print(f"CSS:  {len(data['css'])} chars")
        if data.get("js"):
            print(f"JS:   {len(data['js'])} chars")
        return

    # --- Output ---
    if args.output == "json":
        output_json(data, args.outfile)
    elif args.output == "form":
        output_form(data, args.outfile, autosubmit=not args.no_autosubmit)
    else:
        # Default: open in browser
        open_in_browser(data)


# ---------------------------------------------------------------------------
# Module API — for programmatic use
# ---------------------------------------------------------------------------


def prefill_from_files(
    html_file=None, css_file=None, js_file=None, **kwargs
) -> dict:
    """Build a CodePen prefill payload from individual files."""
    return build_payload(html_file=html_file, css_file=css_file, js_file=js_file, **kwargs)


def prefill_from_html(filepath: str, **kwargs) -> dict:
    """Build a CodePen prefill payload from a single HTML file."""
    return build_payload(single_html=filepath, **kwargs)


def prefill_from_folder(folder: str, **kwargs) -> dict:
    """Build a CodePen prefill payload from a folder of assets."""
    return build_payload(folder=folder, **kwargs)


def prefill_from_strings(
    html: str = "", css: str = "", js: str = "", **kwargs
) -> dict:
    """Build a CodePen prefill payload from raw strings."""
    data = {}
    if html:
        data["html"] = html
    if css:
        data["css"] = css
    if js:
        data["js"] = js
    # Apply overrides
    for key in [
        "title", "description", "private", "layout",
        "html_pre_processor", "css_pre_processor", "css_starter",
        "css_prefix", "js_pre_processor", "html_classes", "head",
        "css_external", "js_external",
    ]:
        if key in kwargs and kwargs[key] is not None:
            data[key] = kwargs[key]
    data = {k: v for k, v in data.items() if v is not None and v != ""}
    return data


def open_pen(data: dict):
    """Open a prefilled pen in the default browser."""
    open_in_browser(data)


def get_form_html(data: dict, autosubmit: bool = True) -> str:
    """Get the HTML form string for embedding."""
    return generate_form_html(data, autosubmit=autosubmit)


def get_batch_html(directory: str) -> str:
    """Get a batch launcher page for a directory of HTML files."""
    return generate_batch_html(directory)


if __name__ == "__main__":
    main()
