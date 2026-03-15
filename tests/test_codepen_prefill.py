#!/usr/bin/env python3
"""
Comprehensive tests for codepen_prefill.py

Tests cover:
  1. Separate file input mode
  2. Single HTML file parsing (lossless extraction)
  3. Folder scanning
  4. Metadata overrides
  5. Preprocessor auto-detection
  6. External resource extraction
  7. JSON output generation
  8. Form HTML generation
  9. Edge cases (empty files, special characters, nested quotes)
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from codepen_prefill import (
    build_payload,
    generate_batch_html,
    generate_form_html,
    move_to_sent,
    parse_single_html,
    prefill_from_strings,
    scan_folder,
)

FIXTURES = Path(__file__).parent / "fixtures"

# ---- Helpers ----

def assert_contains(haystack, needle, msg=""):
    assert needle in haystack, f"Expected to find {needle!r} in output. {msg}\nGot: {haystack[:500]}"

def assert_not_contains(haystack, needle, msg=""):
    assert needle not in haystack, f"Did NOT expect to find {needle!r} in output. {msg}"

# ---- Test: Separate Files ----

def test_separate_files():
    """Individual --html, --css, --js files are read verbatim."""
    data = build_payload(
        html_file=str(FIXTURES / "separate" / "body.html"),
        css_file=str(FIXTURES / "separate" / "style.css"),
        js_file=str(FIXTURES / "separate" / "app.js"),
    )
    assert "html" in data
    assert "css" in data
    assert "js" in data
    assert_contains(data["html"], 'data-greeting="hello"')
    assert_contains(data["css"], "--primary: #47cf73")
    assert_contains(data["js"], "addEventListener")
    print("  PASS: test_separate_files")

# ---- Test: Single HTML Parsing ----

def test_single_html_extraction():
    """Single HTML file is split into html, css, js, externals, head, classes."""
    data = parse_single_html(str(FIXTURES / "single" / "combined.html"))

    # CSS extracted from both <style> blocks
    assert "css" in data
    assert_contains(data["css"], "--accent: #ff6b6b")
    assert_contains(data["css"], ".wrapper")
    assert_contains(data["css"], "#output")

    # JS extracted from inline <script>
    assert "js" in data
    assert_contains(data["js"], "_.range(1, 6)")
    assert_contains(data["js"], "getElementById")

    # External CSS from <link> tags
    assert "css_external" in data
    assert_contains(data["css_external"], "fonts.xz.style")
    assert_contains(data["css_external"], "new.min.css")

    # External JS from <script src="...">
    assert "js_external" in data
    assert_contains(data["js_external"], "lodash.min.js")

    # HTML body content
    assert "html" in data
    assert_contains(data["html"], "Combined HTML Test")
    assert_contains(data["html"], '<div id="output">')

    # No <style> or <script> tags should remain in HTML
    assert_not_contains(data["html"], "<style")
    assert_not_contains(data["html"], "<script")

    # html_classes from <html> tag
    assert data.get("html_classes") == "dark-theme"

    # Title extracted
    assert data.get("title") == "Combined Test Page"

    # Head content (viewport meta should remain)
    assert "head" in data
    assert_contains(data["head"], "viewport")

    print("  PASS: test_single_html_extraction")


def test_single_html_lossless():
    """Verify that all content from the original file is preserved somewhere."""
    original = (FIXTURES / "single" / "combined.html").read_text()
    data = parse_single_html(str(FIXTURES / "single" / "combined.html"))

    # Every meaningful piece of content should appear in some field
    all_content = " ".join(str(v) for v in data.values())

    # Check key content pieces
    assert_contains(all_content, "--accent: #ff6b6b", "CSS variable lost")
    assert_contains(all_content, ".wrapper", "CSS class lost")
    assert_contains(all_content, "_.range(1, 6)", "JS code lost")
    assert_contains(all_content, "Combined HTML Test", "HTML content lost")
    assert_contains(all_content, "fonts.xz.style", "External CSS lost")
    assert_contains(all_content, "lodash.min.js", "External JS lost")
    assert_contains(all_content, "dark-theme", "HTML classes lost")
    assert_contains(all_content, "viewport", "Head meta lost")

    print("  PASS: test_single_html_lossless")


# ---- Test: Folder Scanning ----

def test_folder_scan():
    """Folder scanning picks up index.html + additional CSS/JS files."""
    data = scan_folder(str(FIXTURES / "folder"))

    # HTML from index.html body
    assert "html" in data
    assert_contains(data["html"], "Folder-Based Project")
    assert_contains(data["html"], '<canvas id="canvas"')

    # CSS from styles.css (standalone file)
    assert "css" in data
    assert_contains(data["css"], "box-sizing: border-box")
    assert_contains(data["css"], "#0d1117")

    # JS from draw.js (standalone file)
    assert "js" in data
    assert_contains(data["js"], "getContext('2d')")
    assert_contains(data["js"], "requestAnimationFrame")

    # External CSS from <link> in index.html
    assert "css_external" in data
    assert_contains(data["css_external"], "animate.min.css")

    # Title from index.html
    assert data.get("title") == "Folder Project"

    print("  PASS: test_folder_scan")


# ---- Test: Metadata Overrides ----

def test_metadata_overrides():
    """CLI metadata flags override auto-detected values."""
    data = build_payload(
        single_html=str(FIXTURES / "single" / "combined.html"),
        title="Override Title",
        description="Custom description",
        private=True,
        layout="top",
    )
    assert data["title"] == "Override Title"
    assert data["description"] == "Custom description"
    assert data["private"] is True
    assert data["layout"] == "top"
    print("  PASS: test_metadata_overrides")


# ---- Test: Preprocessor Auto-Detection ----

def test_preprocessor_autodetect():
    """File extensions trigger correct preprocessor settings."""
    # Create temp files with preprocessor extensions
    with tempfile.NamedTemporaryFile(suffix=".scss", mode="w", delete=False) as f:
        f.write("$color: red;\nbody { color: $color; }")
        scss_path = f.name

    with tempfile.NamedTemporaryFile(suffix=".ts", mode="w", delete=False) as f:
        f.write("const x: number = 42;\nconsole.log(x);")
        ts_path = f.name

    with tempfile.NamedTemporaryFile(suffix=".pug", mode="w", delete=False) as f:
        f.write("div.container\n  h1 Hello")
        pug_path = f.name

    try:
        data = build_payload(html_file=pug_path, css_file=scss_path, js_file=ts_path)
        assert data.get("html_pre_processor") == "pug"
        assert data.get("css_pre_processor") == "scss"
        assert data.get("js_pre_processor") == "typescript"
    finally:
        os.unlink(scss_path)
        os.unlink(ts_path)
        os.unlink(pug_path)

    print("  PASS: test_preprocessor_autodetect")


# ---- Test: External Resources ----

def test_external_merge():
    """CLI --css-external and --js-external merge with auto-detected ones."""
    data = build_payload(
        single_html=str(FIXTURES / "single" / "combined.html"),
        css_external="https://example.com/extra.css",
        js_external="https://example.com/extra.js",
    )
    # Should contain both auto-detected and manually added
    assert_contains(data["css_external"], "fonts.xz.style")
    assert_contains(data["css_external"], "example.com/extra.css")
    assert_contains(data["js_external"], "lodash.min.js")
    assert_contains(data["js_external"], "example.com/extra.js")
    print("  PASS: test_external_merge")


# ---- Test: JSON Output ----

def test_json_output():
    """JSON output is valid and contains expected fields."""
    data = build_payload(
        html_file=str(FIXTURES / "separate" / "body.html"),
        css_file=str(FIXTURES / "separate" / "style.css"),
        js_file=str(FIXTURES / "separate" / "app.js"),
        title="JSON Test",
    )
    json_str = json.dumps(data, ensure_ascii=False)
    parsed = json.loads(json_str)
    assert parsed["title"] == "JSON Test"
    assert "html" in parsed
    assert "css" in parsed
    assert "js" in parsed
    print("  PASS: test_json_output")


# ---- Test: Form HTML Generation ----

def test_form_html_generation():
    """Generated form HTML is valid and contains the correct endpoint and data."""
    data = prefill_from_strings(
        html="<h1>Test</h1>",
        css="h1 { color: red; }",
        js="console.log('hi');",
        title="Form Test",
    )
    form = generate_form_html(data, autosubmit=False)

    assert_contains(form, "https://codepen.io/pen/define/")
    assert_contains(form, 'name="data"')
    assert_contains(form, "Form Test")
    assert_contains(form, '<button type="submit">')
    # Verify the JSON is properly escaped in the value attribute
    assert_contains(form, "&lt;h1&gt;Test&lt;/h1&gt;")

    print("  PASS: test_form_html_generation")


def test_form_autosubmit():
    """Autosubmit form includes the auto-submit script."""
    data = prefill_from_strings(html="<p>auto</p>")
    form = generate_form_html(data, autosubmit=True)
    assert_contains(form, '.submit()')
    assert_contains(form, "Opening CodePen")
    print("  PASS: test_form_autosubmit")


# ---- Test: Edge Cases ----

def test_special_characters():
    """HTML with special characters (quotes, angle brackets) is handled correctly."""
    data = prefill_from_strings(
        html='<div data-value="test\'s &amp; stuff">Content with <special> chars</div>',
        title='Title with "quotes" & <brackets>',
    )
    json_str = json.dumps(data, ensure_ascii=False)
    # Must be valid JSON
    parsed = json.loads(json_str)
    assert_contains(parsed["html"], "test's")
    assert_contains(parsed["title"], '"quotes"')

    # Form must properly escape
    form = generate_form_html(data)
    # The JSON inside the value attribute should be HTML-escaped
    assert "&amp;" in form or "&#" in form or "&quot;" in form
    print("  PASS: test_special_characters")


def test_empty_input():
    """Empty files produce empty but valid payload."""
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write("")
        empty_path = f.name
    try:
        data = build_payload(html_file=empty_path)
        # Should not have html key since content is empty
        assert "html" not in data or data.get("html", "") == ""
    finally:
        os.unlink(empty_path)
    print("  PASS: test_empty_input")


def test_prefill_from_strings():
    """The programmatic API works correctly."""
    data = prefill_from_strings(
        html="<p>Hello</p>",
        css="p { color: blue; }",
        js="console.log('world');",
        title="String Test",
        description="A test",
        css_starter="normalize",
        layout="right",
    )
    assert data["html"] == "<p>Hello</p>"
    assert data["css"] == "p { color: blue; }"
    assert data["js"] == "console.log('world');"
    assert data["title"] == "String Test"
    assert data["description"] == "A test"
    assert data["css_starter"] == "normalize"
    assert data["layout"] == "right"
    print("  PASS: test_prefill_from_strings")


def test_html_no_body_tag():
    """HTML fragment without <body> is handled gracefully."""
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write('<div class="widget">\n  <span>No body tag here</span>\n</div>')
        path = f.name
    try:
        data = parse_single_html(path)
        assert "html" in data
        assert_contains(data["html"], "No body tag here")
        assert_contains(data["html"], 'class="widget"')
    finally:
        os.unlink(path)
    print("  PASS: test_html_no_body_tag")


def test_multiple_style_and_script_blocks():
    """Multiple <style> and <script> blocks are all captured."""
    html_content = """<!DOCTYPE html>
<html>
<head>
  <style>.a { color: red; }</style>
  <style>.b { color: blue; }</style>
</head>
<body>
  <div>Content</div>
  <script>var x = 1;</script>
  <script>var y = 2;</script>
  <style>.c { color: green; }</style>
</body>
</html>"""
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write(html_content)
        path = f.name
    try:
        data = parse_single_html(path)
        assert_contains(data["css"], ".a { color: red; }")
        assert_contains(data["css"], ".b { color: blue; }")
        assert_contains(data["css"], ".c { color: green; }")
        assert_contains(data["js"], "var x = 1;")
        assert_contains(data["js"], "var y = 2;")
    finally:
        os.unlink(path)
    print("  PASS: test_multiple_style_and_script_blocks")


# ---- Test: Inbox/Sent Workflow ----

def test_move_to_sent():
    """Files end up in timestamped subdir and are removed from source."""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        src = tmpdir / "source"
        src.mkdir()
        sent = tmpdir / "sent"
        sent.mkdir()

        # Create test files
        f1 = src / "test1.html"
        f2 = src / "test2.html"
        f1.write_text("<h1>Test 1</h1>")
        f2.write_text("<h1>Test 2</h1>")

        move_to_sent([f1, f2], sent)

        # Files should be gone from source
        assert not f1.exists(), "Source file 1 should be removed"
        assert not f2.exists(), "Source file 2 should be removed"

        # Should have exactly one timestamped subdir
        subdirs = list(sent.iterdir())
        assert len(subdirs) == 1, f"Expected 1 subdir in sent, got {len(subdirs)}"
        ts_dir = subdirs[0]
        assert ts_dir.is_dir()

        # Files should be in the timestamped subdir
        moved_files = sorted(f.name for f in ts_dir.iterdir())
        assert moved_files == ["test1.html", "test2.html"]
    finally:
        shutil.rmtree(tmpdir)
    print("  PASS: test_move_to_sent")


def test_generate_batch_with_manifest():
    """With return_manifest=True, returns (str, list) tuple."""
    result = generate_batch_html(str(FIXTURES / "folder"), return_manifest=True)
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2
    page, processed = result
    assert isinstance(page, str)
    assert isinstance(processed, list)
    assert len(processed) > 0
    # All items should be Path objects pointing to .html files
    for p in processed:
        assert p.suffix.lower() == ".html"
    print("  PASS: test_generate_batch_with_manifest")


def test_generate_batch_without_manifest():
    """Without return_manifest, returns str (backward compat)."""
    result = generate_batch_html(str(FIXTURES / "folder"))
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert_contains(result, "CodePen")
    print("  PASS: test_generate_batch_without_manifest")


def test_non_html_files_ignored():
    """Non-HTML files stay in inbox, not in manifest."""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create a mix of HTML and non-HTML files
        (tmpdir / "good.html").write_text("<h1>Good</h1>")
        (tmpdir / "notes.txt").write_text("some notes")
        (tmpdir / "data.json").write_text("{}")
        (tmpdir / "image.png").write_bytes(b"\x89PNG")

        page, processed = generate_batch_html(str(tmpdir), return_manifest=True)

        processed_names = [p.name for p in processed]
        assert "good.html" in processed_names, "HTML file should be in manifest"
        assert "notes.txt" not in processed_names, "TXT file should NOT be in manifest"
        assert "data.json" not in processed_names, "JSON file should NOT be in manifest"
        assert "image.png" not in processed_names, "PNG file should NOT be in manifest"
    finally:
        shutil.rmtree(tmpdir)
    print("  PASS: test_non_html_files_ignored")


# ---- Run All Tests ----

def main():
    tests = [
        test_separate_files,
        test_single_html_extraction,
        test_single_html_lossless,
        test_folder_scan,
        test_metadata_overrides,
        test_preprocessor_autodetect,
        test_external_merge,
        test_json_output,
        test_form_html_generation,
        test_form_autosubmit,
        test_special_characters,
        test_empty_input,
        test_prefill_from_strings,
        test_html_no_body_tag,
        test_multiple_style_and_script_blocks,
        test_move_to_sent,
        test_generate_batch_with_manifest,
        test_generate_batch_without_manifest,
        test_non_html_files_ignored,
    ]

    passed = 0
    failed = 0

    print(f"\nRunning {len(tests)} tests...\n")

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL: {test.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed == 0:
        print("All tests passed!")
    else:
        print(f"{failed} test(s) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
