#!/usr/bin/env python3
"""Validate the buildless Vafrcor Studio GitHub Pages site."""

import hashlib
from html.parser import HTMLParser
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PAGES = {
    "index.html": "en",
    "id/index.html": "id",
    "kid-achievements/index.html": "en",
    "kid-achievements/id/index.html": "id",
    "kid-achievements/privacy/index.html": "en",
    "kid-achievements/privacy/id/index.html": "id",
    "kid-achievements/terms/index.html": "en",
    "kid-achievements/terms/id/index.html": "id",
}
VERIFICATION_FILE = "googleb51d7a67d4f85c0c.html"
VERIFICATION_SHA256 = (
    "4a7274d330b6c0a0d883f8bbecf5b48477e5f976ef6b03398bce1d495757ee35"
)
REQUIRED_EMAIL = "vafrcor2009@gmail.com"
UNFINISHED_MARKERS = (
    "TO" + "DO",
    "T" + "BD",
    "YOUR" + "_",
    "example" + ".com",
    "lorem" + " ipsum",
)
FORBIDDEN_ELEMENTS = {"script", "form", "iframe"}
PAGE_REQUIREMENTS = {
    "index.html": (
        "Vafrcor Studio",
        "privacy-focused mobile applications",
        "/kid-achievements/",
    ),
    "id/index.html": (
        "Vafrcor Studio",
        "aplikasi seluler yang berfokus pada privasi",
        "/kid-achievements/id/",
    ),
    "kid-achievements/index.html": (
        "Kid Achievements",
        "offline",
        "parent",
        "kid",
        "approve",
        "points",
        "rewards",
        "Google Drive",
        "encrypted",
        "Android 7.0",
        "API 24",
        "/kid-achievements/privacy/",
        "/kid-achievements/terms/",
    ),
    "kid-achievements/id/index.html": (
        "Kid Achievements",
        "offline",
        "orang tua",
        "anak",
        "menyetujui",
        "poin",
        "hadiah",
        "Google Drive",
        "terenkripsi",
        "Android 7.0",
        "API 24",
        "/kid-achievements/privacy/id/",
        "/kid-achievements/terms/id/",
    ),
    "kid-achievements/privacy/index.html": (
        "SQLite",
        "registered parent email",
        "Google account",
        "drive.appdata",
        "encrypted",
        "passphrase",
        "does not operate a synchronization server",
        "no advertising",
        "no analytics",
        "does not sell",
        "Android",
        "biometric",
        "notifications",
        "parent",
        "delete",
        "Google Privacy Policy",
        "Contact support",
        "November 1, 2026",
    ),
    "kid-achievements/privacy/id/index.html": (
        "SQLite",
        "email orang tua terdaftar",
        "akun Google",
        "drive.appdata",
        "dienkripsi",
        "frasa sandi",
        "tidak mengoperasikan server sinkronisasi",
        "tanpa iklan",
        "tanpa analitik",
        "tidak menjual",
        "Android",
        "biometrik",
        "notifikasi",
        "orang tua",
        "menghapus",
        "Kebijakan Privasi Google",
        "Hubungi dukungan",
        "1 November 2026",
    ),
    "kid-achievements/terms/index.html": (
        "private family use",
        "parent or guardian",
        "credentials",
        "passphrase",
        "backups",
        "Google services",
        "availability",
        "synchronization",
        "acceptable use",
        "applicable law",
        "ending use",
        "changes to these terms",
        "Contact support",
        "November 1, 2026",
    ),
    "kid-achievements/terms/id/index.html": (
        "penggunaan keluarga secara privat",
        "orang tua atau wali",
        "kredensial",
        "frasa sandi",
        "cadangan",
        "layanan Google",
        "ketersediaan",
        "sinkronisasi",
        "penggunaan yang dapat diterima",
        "hukum yang berlaku",
        "mengakhiri penggunaan",
        "perubahan ketentuan",
        "Hubungi dukungan",
        "1 November 2026",
    ),
}
FORBIDDEN_PAGE_CLAIMS = {
    "kid-achievements/privacy/index.html": (
        "we collect fingerprints",
        "our synchronization server",
    ),
    "kid-achievements/privacy/id/index.html": (
        "kami mengumpulkan sidik jari",
        "server sinkronisasi kami",
    ),
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.language = ""
        self.title_parts: list[str] = []
        self.description = ""
        self.has_viewport = False
        self.h1_count = 0
        self.stylesheets: list[str] = []
        self.anchors: list[str] = []
        self.forbidden_elements: list[str] = []
        self.external_assets: list[str] = []
        self.text_parts: list[str] = []
        self._in_title = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "html":
            self.language = attributes.get("lang", "") or ""
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (attributes.get("name") or "").lower()
            if name == "description":
                self.description = attributes.get("content", "") or ""
            elif name == "viewport":
                self.has_viewport = bool(attributes.get("content"))
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a":
            href = attributes.get("href")
            if href:
                self.anchors.append(href)
        elif tag == "link" and (attributes.get("rel") or "").lower() == "stylesheet":
            href = attributes.get("href", "") or ""
            self.stylesheets.append(href)
            if href.startswith(("http://", "https://", "//")):
                self.external_assets.append(href)

        if tag in FORBIDDEN_ELEMENTS:
            self.forbidden_elements.append(tag)

        if tag in {"img", "source"}:
            source = attributes.get("src", "") or ""
            if source.startswith(("http://", "https://", "//")):
                self.external_assets.append(source)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        self.text_parts.append(text)
        if self._in_title:
            self.title_parts.append(text)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts)

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)


def resolve_internal_link(href: str) -> Path | None:
    if not href.startswith("/") or href.startswith("//"):
        return None
    clean_path = href.split("#", 1)[0].split("?", 1)[0]
    if clean_path == "/":
        return ROOT / "index.html"
    relative = clean_path.removeprefix("/")
    if clean_path.endswith("/"):
        relative += "index.html"
    return ROOT / relative


def validate_page(relative_path: str, expected_language: str) -> list[str]:
    errors: list[str] = []
    path = ROOT / relative_path
    if not path.is_file():
        return [f"{relative_path}: required page is missing"]

    source = path.read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(source)

    if parser.language != expected_language:
        errors.append(
            f"{relative_path}: expected lang={expected_language!r}, "
            f"found {parser.language!r}"
        )
    if not parser.title:
        errors.append(f"{relative_path}: title is missing")
    if not parser.description:
        errors.append(f"{relative_path}: meta description is missing")
    if not parser.has_viewport:
        errors.append(f"{relative_path}: viewport metadata is missing")
    if parser.h1_count != 1:
        errors.append(f"{relative_path}: expected one h1, found {parser.h1_count}")
    if "/assets/site.css" not in parser.stylesheets:
        errors.append(f"{relative_path}: /assets/site.css is missing")
    if REQUIRED_EMAIL not in source:
        errors.append(f"{relative_path}: support email is missing")
    for element in parser.forbidden_elements:
        errors.append(f"{relative_path}: forbidden <{element}> element")
    for asset in parser.external_assets:
        errors.append(f"{relative_path}: external runtime asset {asset!r}")

    lowered_source = source.lower()
    for marker in UNFINISHED_MARKERS:
        if marker.lower() in lowered_source:
            errors.append(f"{relative_path}: unfinished marker {marker!r}")

    for required_text in PAGE_REQUIREMENTS.get(relative_path, ()):
        if required_text.lower() not in lowered_source:
            errors.append(
                f"{relative_path}: required content is missing: {required_text!r}"
            )
    for forbidden_claim in FORBIDDEN_PAGE_CLAIMS.get(relative_path, ()):
        if forbidden_claim.lower() in lowered_source:
            errors.append(
                f"{relative_path}: prohibited claim found: {forbidden_claim!r}"
            )

    for href in parser.anchors:
        if href.startswith("http:"):
            errors.append(f"{relative_path}: insecure link {href!r}")
        target = resolve_internal_link(href)
        if target is not None and not target.is_file():
            errors.append(
                f"{relative_path}: internal link target is missing: {href!r}"
            )
        if relative_path in {
            "kid-achievements/index.html",
            "kid-achievements/id/index.html",
        } and (href.lower().endswith(".apk") or "download" in href.lower()):
            errors.append(f"{relative_path}: public download link is forbidden")
    return errors


def validate_verification_file() -> list[str]:
    path = ROOT / VERIFICATION_FILE
    if not path.is_file():
        return [f"{VERIFICATION_FILE}: verification file is missing"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != VERIFICATION_SHA256:
        return [f"{VERIFICATION_FILE}: verification file digest changed"]
    return []


def main() -> int:
    errors = validate_verification_file()
    for relative_path, language in REQUIRED_PAGES.items():
        errors.extend(validate_page(relative_path, language))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Site validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
