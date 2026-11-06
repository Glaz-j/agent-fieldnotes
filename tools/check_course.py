#!/usr/bin/env python3
"""Check the built reading pages, local links, captions and experiment download."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.links, self.ids, self.videos, self.buttons = [], set(), [], []
        self.source = path.read_text()
        self.feed(self.source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.ids, "Duplicate HTML id: " + attrs["id"]
            self.ids.add(attrs["id"])
        for key in ("href", "src", "poster"):
            if attrs.get(key):
                self.links.append(attrs[key])
        if tag == "video":
            self.videos.append(attrs)
        if tag == "button" and "data-seek" in attrs:
            self.buttons.append(attrs)


pages = {p: Page(p) for p in [DOCS / "index.html", DOCS / "start.html", *sorted((DOCS / "learn").glob("*.html"))]}
gallery_ids = {"demo-" + d["id"] for d in json.loads((DOCS / "data/showcase.json").read_text())["demos"]}
links = videos = 0
for path, page in pages.items():
    assert "<!-- course-demo:" not in page.source, path
    for raw in page.links:
        ref = urlsplit(raw)
        if ref.scheme or ref.netloc:
            continue
        target = (path.parent / unquote(ref.path)).resolve() if ref.path else path
        assert target.is_relative_to(DOCS), (path, raw, "outside docs")
        assert target.is_file(), (path, raw, "missing target")
        if ref.fragment and target.suffix == ".html":
            parsed = pages.get(target) or Page(target)
            allowed = gallery_ids | {"gallery", "routes", "method"} if target.name == "gallery.html" else set()
            assert unquote(ref.fragment) in parsed.ids | allowed, (path, raw, "missing anchor")
        links += 1
    for attrs in page.videos:
        assert "controls" in attrs and "playsinline" in attrs
        assert "autoplay" not in attrs and attrs.get("aria-label")
        videos += 1

manifest = json.loads((DOCS / "course-media/recordings-manifest.json").read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((DOCS / "course-media" / name).read_bytes()).hexdigest() == digest, name
for p in (DOCS / "course-media").glob("course-*.json"):
    record = json.loads(p.read_text())
    assert record["model_calls"] == 0
    for name, digest in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, (p, name, "recording source changed")
    assert all(0 <= c["start"] < c["end"] <= record["duration_s"] for c in record["cues"])
    assert p.with_suffix(".vtt").read_text().startswith("WEBVTT\n")
    assert p.with_suffix(".mp4").is_file() and p.with_suffix(".png").is_file()

with zipfile.ZipFile(DOCS / "downloads/agent-fieldnotes-lab.zip") as archive:
    for name in archive.namelist():
        assert archive.read(name) == (ROOT / name).read_bytes(), name
    source_count = len(archive.namelist())
assert len(pages) == 18
print(f"{len(pages)} course pages; {links} local links/assets/anchors; {videos} accessible videos; {source_count} matching lab files: OK")
