"""Build a static GitHub Pages preview of the Vastra storefront.

GitHub Pages cannot run Django. This script renders the public catalogue once,
copies its CSS/JS/images into ``docs/assets``, and writes a self-contained
``index.html`` (plus a root copy) so either Pages source setting works.

Accounts, cart POSTs and the admin are unavailable on the static preview; their
links simply return to the catalogue page.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.test import Client

DOCS_DIR = BASE_DIR / "docs"
ASSETS_DIR = DOCS_DIR / "assets"

def copy_assets() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        BASE_DIR / "boutique" / "static" / "boutique",
        ASSETS_DIR / "boutique",
        dirs_exist_ok=True,
    )
    # Older previews used assets/media; keep the published tree clean.
    stale_media = ASSETS_DIR / "media"
    if stale_media.exists():
        shutil.rmtree(stale_media)
    shutil.copytree(
        BASE_DIR / "media",
        ASSETS_DIR / "product-images",
        dirs_exist_ok=True,
    )


def render_storefront() -> str:
    response = Client().get("/")
    if response.status_code != 200:
        raise RuntimeError(f"Storefront returned HTTP {response.status_code}")
    return response.content.decode("utf-8")


def rewrite(html: str, asset_prefix: str) -> str:
    html = html.replace("/static/boutique/", f"{asset_prefix}boutique/")
    html = html.replace("/media/", f"{asset_prefix}product-images/")

    # Django URLs that need a server have no meaning on static hosting.
    html = re.sub(r'href="/\?[^"]*"', 'href="index.html#products"', html)
    html = re.sub(r'action="/#[^"]*"', 'action="index.html#products"', html)
    html = re.sub(r'href="/login/[^"]*"', 'href="index.html"', html)
    html = re.sub(r'href="/signup/[^"]*"', 'href="index.html"', html)
    html = re.sub(r'href="/admin/[^"]*"', 'href="index.html"', html)
    html = html.replace('href="/"', 'href="index.html"')

    return html


def main() -> None:
    copy_assets()
    html = render_storefront()

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(rewrite(html, "assets/"), encoding="utf-8")
    (BASE_DIR / "index.html").write_text(rewrite(html, "docs/assets/"), encoding="utf-8")
    (DOCS_DIR / ".nojekyll").touch()
    (BASE_DIR / ".nojekyll").touch()

    print("Static preview written to docs/index.html and index.html")


if __name__ == "__main__":
    main()
