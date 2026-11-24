"""Build an interactive static GitHub Pages preview of the Vastra storefront.

GitHub Pages cannot run Django. This script renders the public catalogue once,
copies its CSS/JS/images into ``docs/assets``, then adds a small browser layer so
categories, search, sign-up, sign-in and the cart work on static hosting.

Accounts and carts live in the visitor's browser (localStorage); they are not
sent to a server and there is no admin on the Pages preview.
"""

from __future__ import annotations

import json
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

from boutique.models import Dress
from boutique.views import CATEGORY_TILES
from django.test import Client

DOCS_DIR = BASE_DIR / "docs"
ASSETS_DIR = DOCS_DIR / "assets"

MODALS = """
<div class="va-modal" id="login-modal" hidden>
  <div class="va-modal-backdrop" data-close-modal></div>
  <div class="va-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="login-title">
    <button type="button" class="modal-close" data-close-modal aria-label="Close">×</button>
    <h2 id="login-title">Sign in</h2>
    <p class="va-modal-sub">Welcome back to Vastra.</p>
    <form id="login-form" novalidate>
      <label>Username<input type="text" name="username" autocomplete="username" required></label>
      <label>Password<input type="password" name="password" autocomplete="current-password" required></label>
      <p class="va-error" data-error hidden></p>
      <button type="submit" class="store-btn primary full">Sign in</button>
    </form>
    <p class="va-switch">New here? <button type="button" data-open-signup>Create account</button></p>
  </div>
</div>

<div class="va-modal" id="signup-modal" hidden>
  <div class="va-modal-backdrop" data-close-modal></div>
  <div class="va-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="signup-title">
    <button type="button" class="modal-close" data-close-modal aria-label="Close">×</button>
    <h2 id="signup-title">Create account</h2>
    <p class="va-modal-sub">A few details and you are ready to shop.</p>
    <form id="signup-form" novalidate>
      <label>Username<input type="text" name="username" autocomplete="username" required></label>
      <label>Phone number<input type="tel" name="phone" autocomplete="tel" required></label>
      <label>Address<textarea name="address" autocomplete="street-address" required></textarea></label>
      <label>Password<input type="password" name="password" autocomplete="new-password" required></label>
      <p class="va-error" data-error hidden></p>
      <button type="submit" class="store-btn primary full">Create account</button>
    </form>
    <p class="va-switch">Already have an account? <button type="button" data-open-login>Sign in</button></p>
  </div>
</div>

<div class="va-toast" id="va-toast" role="status" hidden></div>
"""


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
    shutil.copy2(
        BASE_DIR / "scripts" / "static_preview.js", ASSETS_DIR / "static-preview.js"
    )
    shutil.copy2(
        BASE_DIR / "scripts" / "static_preview.css", ASSETS_DIR / "static-preview.css"
    )


def render_storefront() -> str:
    response = Client().get("/")
    if response.status_code != 200:
        raise RuntimeError(f"Storefront returned HTTP {response.status_code}")
    return response.content.decode("utf-8")


def build_data(asset_prefix: str) -> dict:
    products = []
    for dress in Dress.objects.filter(is_active=True)[:12]:
        image = ""
        if dress.image:
            image = dress.image.url.replace(
                "/media/", f"{asset_prefix}product-images/"
            )
        products.append(
            {
                "code": dress.code,
                "name": dress.name,
                "category": dress.category,
                "categoryLabel": dress.get_category_display(),
                "size": dress.size,
                "color": dress.color,
                "fabric": dress.fabric,
                "price": str(dress.price),
                "stock": dress.quantity,
                "description": dress.description,
                "available": dress.is_available,
                "image": image,
            }
        )

    return {
        "products": products,
        "categories": [
            {"value": value, "label": label} for value, label, _image in CATEGORY_TILES
        ],
    }


def rewrite(html: str, asset_prefix: str, data: dict) -> str:
    html = html.replace("/static/boutique/", f"{asset_prefix}boutique/")
    html = html.replace("/media/", f"{asset_prefix}product-images/")

    # Search stays on the page instead of posting back to Django.
    html = html.replace(
        '<form class="store-search-form"',
        '<form class="store-search-form" data-static-search',
        1,
    )
    html = html.replace('action="index.html#products"', 'action="#products"')
    html = html.replace(
        "</form>",
        '</form>\n          <a class="store-search-clear" href="#products" data-clear-search hidden>Clear</a>',
        1,
    )

    # Header account actions become interactive controls.
    html = re.sub(
        r'<div class="store-actions">.*?<button type="button" class="cart-button"',
        lambda _match: (
            '<div class="store-actions">\n'
            '          <button type="button" class="store-link link-button" '
            'data-header-login data-open-login>Sign in</button>\n'
            '          <button type="button" class="store-link link-button" '
            'data-header-signup data-open-signup>Create account</button>\n'
            '          <span class="account-chip" data-account-chip hidden></span>\n'
            '          <button type="button" class="store-link link-button" '
            'data-logout hidden>Sign out</button>\n'
            '          <button type="button" class="cart-button"'
        ),
        html,
        count=1,
        flags=re.DOTALL,
    )

    # Category tiles filter the product grid in the browser.
    html = re.sub(
        r'href="\?category=([A-Z_]+)#products"',
        lambda match: f'href="#products" data-category="{match.group(1)}"',
        html,
    )

    # Remove Django-rendered cards; JavaScript re-renders them from the data.
    html = re.sub(
        r'\s*<article class="product-card">.*?</article>',
        "",
        html,
        flags=re.DOTALL,
    )
    html = html.replace(
        '<div class="product-grid">',
        '<div class="product-grid" id="static-product-results">',
        1,
    )

    # Cart drawer becomes a live, per-account cart.
    html = html.replace(
        '<span class="cart-count">', '<span class="cart-count" data-cart-count>', 1
    )
    html = re.sub(
        r'<div class="cart-body">.*?</div>\s*<div class="cart-foot">',
        '<div class="cart-body" data-cart-body></div>\n    <div class="cart-foot">',
        html,
        count=1,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<div class="cart-foot">.*?</aside>',
        lambda _match: (
            '<div class="cart-foot">\n'
            '      <div class="cart-total"><span>Total</span>'
            '<strong data-cart-total>₹0.00</strong></div>\n'
            '      <p class="cart-hint">Your cart is saved to your account. '
            "The boutique will confirm stock when you get in touch.</p>\n"
            '      <button type="button" class="store-btn primary full" '
            'data-cart-cta data-open-login>Sign in to add items</button>\n'
            "    </div>\n"
            "  </aside>"
        ),
        html,
        count=1,
        flags=re.DOTALL,
    )

    # Load the browser layer and its styles.
    html = html.replace(
        "</head>",
        f'<link rel="stylesheet" href="{asset_prefix}static-preview.css?v=4">\n</head>',
        1,
    )
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace(
        "</body>",
        (
            f'<script id="vastra-static-data" type="application/json">{payload}</script>\n'
            f"{MODALS}\n"
            f'<script src="{asset_prefix}static-preview.js?v=4"></script>\n'
            "</body>"
        ),
        1,
    )

    return html


def main() -> None:
    copy_assets()
    html = render_storefront()

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(
        rewrite(html, "assets/", build_data("assets/")), encoding="utf-8"
    )
    (BASE_DIR / "index.html").write_text(
        rewrite(html, "docs/assets/", build_data("docs/assets/")), encoding="utf-8"
    )
    (DOCS_DIR / ".nojekyll").touch()
    (BASE_DIR / ".nojekyll").touch()

    print("Interactive static preview written to docs/index.html and index.html")


if __name__ == "__main__":
    main()
