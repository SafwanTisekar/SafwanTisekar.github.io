"""Checks for the published site: numbers, links, accessibility and publishing rules.

The pages are static. The numbers and project cards are written by ``make site`` in the
project repositories (for the Dubai project: dubai-property-analytics), which also checks
them against their sources; these tests check what is committed here, and the Pages
workflow runs them before every deploy.

Run: ``pip install -r requirements-dev.txt && pytest``.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from PIL import Image

SITE = Path(__file__).resolve().parents[1]
HOME = SITE / "index.html"
PROJECT = SITE / "projects" / "dubai-property" / "index.html"
PAGES = {"home": HOME, "project": PROJECT}
TEXT_SUFFIXES = {".html", ".css", ".js", ".json", ".svg", ".txt", ".md"}
# Repository files that are not part of the site (the deploy workflow leaves them out).
NOT_PUBLISHED = {".git", ".github", "tests", "README.md", "requirements-dev.txt", ".gitignore"}

# Same patterns as the build (dubai_property.website.build) that writes the spans and cards.
SPAN_RE = re.compile(r'(<span\b[^>]*\bdata-kpi="([a-z0-9_]+)"[^>]*>)(.*?)(</span>)', re.DOTALL)
PLACEHOLDER_RE = re.compile(r"\{([a-z0-9_]+)\}")


class Page(HTMLParser):
    """Collects tags and ids from a page, and which images are decorative by design."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.ids: set[str] = set()
        self.decorative_ok: set[int] = set()  # <img> inside a labelled button
        self._button_depth = 0
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "button":
            self._button_depth += 1
        if tag == "img" and self._button_depth:
            self.decorative_ok.add(len(self.tags))
        self.tags.append((tag, a))

    def handle_endtag(self, tag: str) -> None:
        if tag == "button":
            self._button_depth -= 1


@pytest.fixture(scope="module")
def pages() -> dict[str, Page]:
    return {name: Page(path) for name, path in PAGES.items()}


@pytest.fixture(scope="module", params=list(PAGES))
def page(request, pages: dict[str, Page]) -> Page:
    return pages[request.param]


@pytest.fixture(scope="module")
def site_json() -> dict:
    return json.loads((SITE / "data" / "site.json").read_text(encoding="utf-8"))


def published_files() -> list[Path]:
    """Every file the deploy publishes."""
    out = []
    for path in SITE.rglob("*"):
        rel = path.relative_to(SITE)
        if path.is_file() and rel.parts[0] not in NOT_PUBLISHED and "__pycache__" not in rel.parts:
            out.append(path)
    return out


def text_files(include_readme: bool = True) -> list[Path]:
    files = [p for p in published_files() if p.suffix in TEXT_SUFFIXES]
    return files + [SITE / "README.md"] if include_readme else files


def resolve(page: Path, url: str) -> tuple[Path, str]:
    """A local link -> (file it opens, fragment). Root-relative links start at the site root."""
    parts = urlsplit(url)
    if not parts.path:
        return page, parts.fragment
    base = SITE / parts.path.lstrip("/") if parts.path.startswith("/") else page.parent / parts.path
    target = base.resolve()
    if parts.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target, parts.fragment


# --- Numbers come from site.json (written by make site), not typed --------------------


def test_every_number_matches_site_json(site_json: dict) -> None:
    kpis = site_json["kpis"]
    seen: set[str] = set()
    for name, path in PAGES.items():
        spans = SPAN_RE.findall(path.read_text(encoding="utf-8"))
        assert spans, f"{name}: no data-kpi spans"
        for _, key, text, _ in spans:
            assert key in kpis, f"{name}: data-kpi={key} is not in site.json"
            assert text == kpis[key]["value"].replace("&", "&amp;"), f"{name} {key}: {text!r}"
            seen.add(key)
    assert not set(kpis) - seen, f"site.json values on no page: {set(kpis) - seen}"


def test_every_kpi_has_label_and_source(site_json: dict) -> None:
    for key, kpi in site_json["kpis"].items():
        assert kpi["value"] and kpi["label"] and kpi["source"], key


def test_project_cards_match_projects_json(site_json: dict) -> None:
    projects = json.loads((SITE / "data" / "projects.json").read_text())["projects"]
    home = HOME.read_text(encoding="utf-8")
    block = home[home.index("<!-- projects:start") : home.index("<!-- projects:end -->")]
    assert block.count('<article class="card"') == len(projects)
    for p in projects:
        assert f'id="project-{p["slug"]}"' in block
        assert p["url"].startswith("/") and p["thumbnail"].startswith("/")
        assert (SITE / p["url"].lstrip("/") / "index.html").is_file(), p["url"]
        for n in p["numbers"]:
            assert n["kpi"] in site_json["kpis"]
            for key in PLACEHOLDER_RE.findall(n["text"]):
                assert key in site_json["kpis"], key


# --- Links, images, accessibility -------------------------------------------------------


def test_local_links_are_root_relative(page: Page) -> None:
    """Every local link starts at the site root, so pages work at any depth."""
    for tag, a in page.tags:
        for attr in ("href", "src"):
            url = a.get(attr)
            if url and not url.startswith(("https://", "http://", "#", "/")):
                pytest.fail(f"{page.path.relative_to(SITE)}: <{tag} {attr}={url}> is not root-relative")


def test_local_links_and_assets_resolve(page: Page, pages: dict[str, Page]) -> None:
    by_path = {p.path.resolve(): p for p in pages.values()}
    for tag, a in page.tags:
        for attr in ("href", "src"):
            url = a.get(attr)
            if not url or url.startswith(("http://", "https://")):
                continue
            target, fragment = resolve(page.path, url)
            assert target.is_file(), f"{page.path.name}: <{tag} {attr}={url}> missing"
            assert SITE in target.parents, f"{url} leaves the site"
            if fragment and target.suffix == ".html":
                assert fragment in by_path[target].ids, f"{url}: no id {fragment!r}"


def test_images_have_alt_text_and_true_sizes(page: Page) -> None:
    for i, (tag, a) in enumerate(page.tags):
        if tag != "img":
            continue
        assert "alt" in a, f"{a.get('src')}: no alt attribute"
        if i not in page.decorative_ok:
            assert (a["alt"] or "").strip(), f"{a.get('src')}: empty alt text"
        target, _ = resolve(page.path, a["src"])
        w, h = Image.open(target).size
        # The declared size reserves the layout space (no shift while images load).
        assert (int(a["width"]), int(a["height"])) == (w, h), f"{a['src']}: is {w}x{h}"


def test_page_basics(page: Page) -> None:
    html = page.path.read_text(encoding="utf-8")
    assert '<html lang="en">' in html
    assert 'name="viewport"' in html and 'name="description"' in html
    (og,) = re.findall(r'property="og:image" content="([^"]+)"', html)
    assert og.startswith("https://safwantisekar.github.io/"), "og:image must be an absolute URL"
    assert (SITE / og.removeprefix("https://safwantisekar.github.io/")).is_file(), og
    assert sum(1 for t, _ in page.tags if t == "h1") == 1
    assert "main" in page.ids


def test_sections(pages: dict[str, Page]) -> None:
    home = {"what-i-do", "about", "experience", "skills", "projects", "education"}
    assert home <= pages["home"].ids
    assert {"report", "story", "build"} <= pages["project"].ids
    project_links = [a.get("href") for _, a in pages["project"].tags if a.get("href")]
    assert "/#projects" in project_links, "project page needs an All projects link"


def test_photo(pages: dict[str, Page]) -> None:
    """Owner photo: WebP under 150 KB, alt text is the owner's name."""
    photo = SITE / "assets" / "photo.webp"
    assert photo.stat().st_size < 150_000
    imgs = [a for t, a in pages["home"].tags if t == "img" and a.get("src") == "/assets/photo.webp"]
    assert imgs and imgs[0]["alt"] == "Safwan Tisekar"


def test_fonts_self_hosted() -> None:
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    for url in re.findall(r"url\(\"?([^\")]+)", css):
        assert url.startswith("/"), url
        assert (SITE / url.lstrip("/")).is_file(), url
    assert (SITE / "assets" / "fonts" / "OFL.txt").is_file(), "ship the font licence"


def test_iframe_title_set_by_script() -> None:
    js = (SITE / "main.js").read_text(encoding="utf-8")
    assert "iframe.title =" in js


def test_no_external_scripts_or_styles(page: Page) -> None:
    for tag, a in page.tags:
        if tag == "script" and a.get("src"):
            assert not a["src"].startswith(("http:", "https:", "//")), a["src"]
        if tag == "link" and a.get("rel") == "stylesheet":
            assert not a["href"].startswith(("http:", "https:", "//")), a["href"]


def test_footer_links(page: Page) -> None:
    html = page.path.read_text(encoding="utf-8")
    footer = html[html.index('<footer class="site-footer">') :]
    assert "Safwan Tisekar" in footer and 'href="#top"' in footer and "Back to top" in footer
    assert 'data-config-href="githubProfileUrl"' in footer
    assert "top" in page.ids


def test_charts_open_in_viewer() -> None:
    """Every chart and report screenshot link opens the accessible viewer (main.js)."""
    html = PROJECT.read_text(encoding="utf-8")
    assert html.count('<figure class="chart">') == html.count('<span class="zoom-hint"')
    for block in re.findall(r'<figure class="chart">.*?</figure>', html, re.DOTALL):
        assert 'class="zoomable"' in block
    js = (SITE / "main.js").read_text(encoding="utf-8")
    assert "showModal()" in js and 'createElement("dialog")' in js


# --- Publishing rules -----------------------------------------------------------------


def test_config_links_exist(page: Page) -> None:
    cfg = (SITE / "config.js").read_text(encoding="utf-8")
    for _, a in page.tags:
        key = a.get("data-config-href")
        if key:
            assert re.search(rf"^\s*{key}:", cfg, re.M), f"config.js has no {key}"


def test_config_points_at_github() -> None:
    cfg = (SITE / "config.js").read_text(encoding="utf-8")
    assert 'repoUrl: "https://github.com/SafwanTisekar/dubai-property-analytics"' in cfg
    assert 'githubProfileUrl: "https://github.com/SafwanTisekar"' in cfg
    assert re.search(r'embedUrl:\s*"https://app\.fabric\.microsoft\.com/view\?r=', cfg)


def test_cv_hidden_until_configured() -> None:
    cfg = (SITE / "config.js").read_text(encoding="utf-8")
    (cv_url,) = re.findall(r'^\s*cvUrl:\s*"([^"]*)"', cfg, re.M)
    home = HOME.read_text(encoding="utf-8")
    assert re.search(r'<a [^>]*id="cv-link"[^>]*\bhidden\b', home), "CV button must start hidden"
    if cv_url:  # a sanitised CV the owner supplied
        assert (SITE / cv_url.lstrip("/")).is_file(), cv_url


def test_project_attribution_and_disclaimer() -> None:
    html = PROJECT.read_text(encoding="utf-8")
    footer = html[html.index('<footer class="site-footer">') :]
    for text in (
        "Dubai Land Department, CC BY 4.0",
        "OpenStreetMap contributors (ODbL)",
        "not affiliated with DLD",
        "Not investment or lending advice",
    ):
        assert text in footer, text
    # The home card shows DLD-derived numbers, so it carries the attribution too.
    assert "Dubai Land Department, CC BY 4.0" in HOME.read_text(encoding="utf-8")


def test_no_em_dashes() -> None:
    for path in text_files():
        assert "—" not in path.read_text(encoding="utf-8"), f"em-dash in {path.name}"


def test_no_open_owner_todos() -> None:
    for path in text_files(include_readme=False):
        assert "TODO(owner)" not in path.read_text(encoding="utf-8"), path.name


# Owner decision (2026-10-03): the site shows GitHub links only. No email, phone, LinkedIn,
# home address, date of birth or visa details, and no CV file unless a sanitised one is set.
# The samples in test_contact_patterns_catch_examples are made up (this repo is public).
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(
    r"\+\d{1,3}[\s.-]?\(?\d{1,4}\)?([\s.-]?\d{2,4}){2,4}"  # international: +971-50..., +44 20 ...
    r"|\b0\d{1,2}[\s.-]?\d{3}[\s.-]?\d{4}\b"  # national: 050 123 4567, 04-123-4567
    r"|\b\d{9,}\b"  # any long digit run
)
PERSONAL = ("mailto:", "tel:", "linkedin", "golden visa", "date of birth", "united arab emirates")


def test_no_personal_contact_details() -> None:
    for path in text_files():
        text = path.read_text(encoding="utf-8")
        assert not EMAIL.search(text), f"email address in {path.name}"
        m = PHONE.search(text)
        assert not m, f"phone-like number {m.group(0)!r} in {path.relative_to(SITE)}"
        lower = text.lower()
        for word in PERSONAL:
            assert word not in lower, f"{word!r} in {path.relative_to(SITE)}"


def test_no_documents_published() -> None:
    """No CV or other document files: only the page assets."""
    allowed = TEXT_SUFFIXES | {".webp", ".png", ".jpg", ".ico", ".woff2", ""}
    for path in published_files():
        assert path.suffix.lower() in allowed, f"{path.relative_to(SITE)} is not a page asset"


def test_contact_patterns_catch_examples() -> None:
    for sample in ("+971-500000000", "+971 50 000 0000", "050 000 0000", "0500000000"):
        assert PHONE.search(sample), sample
    for sample in ("AED 668.3bn", "275,702", "1.77M", "2026-10-02", "25 Sep 2026", "+4.6%"):
        assert not PHONE.search(sample), sample
    assert EMAIL.search("someone@example.com")


# --- Colour contrast (WCAG AA, 4.5:1 for text) -------------------------------------------


def _luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def tokens(css: str, selector: str) -> dict[str, str]:
    block = css[css.index(selector) :]
    block = block[: block.index("}")]
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))


def test_colour_contrast() -> None:
    """Dark theme: every text colour on every surface it sits on, and the light chart cards."""
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    t = tokens(css, ":root {")
    pairs = [
        ("text", "bg"), ("text", "surface"), ("text", "surface-2"),
        ("muted", "bg"), ("muted", "surface"), ("muted", "surface-2"),
        ("accent", "bg"), ("accent", "surface"), ("accent", "surface-2"),
        ("accent-strong", "bg"), ("accent-strong", "surface"),
        ("on-accent", "accent"), ("on-accent", "accent-strong"),
        ("light-text", "light-card"), ("light-muted", "light-card"),
    ]  # fmt: skip
    for fg, bg in pairs:
        ratio = contrast(t[fg], t[bg])
        assert ratio >= 4.5, f"--{fg} on --{bg} is {ratio:.2f}:1"
    # Focus ring (a UI component, 3:1) against the page and cards.
    for bg in ("bg", "surface"):
        assert contrast(t["accent-strong"], t[bg]) >= 3
    assert contrast("#5c4400", "#fff4cc") >= 4.5  # the owner-TODO note style
