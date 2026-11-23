"""Capture screenshots of the customer storefront.

Optional developer tool: requires Playwright and an installed Chrome/Chromium.
Run the dev server with a populated catalogue first:

    python manage.py migrate
    python manage.py seed_demo
    python manage.py runserver

    python scripts/capture_screenshots.py
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "screenshots"


def capture(page, filename: str) -> None:
    page.wait_for_load_state("load")
    page.screenshot(
        path=str(OUTPUT_DIR / filename),
        full_page=True,
        timeout=120_000,
        animations="disabled",
    )
    print(f"saved {filename}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-gpu", "--disable-software-rasterizer"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 950})

        # 1. Public storefront
        page.goto(BASE_URL)
        capture(page, "01-storefront.png")

        # 2. Sign-in and sign-up screens
        page.goto(f"{BASE_URL}/login/")
        capture(page, "02-login.png")

        page.goto(f"{BASE_URL}/signup/")
        capture(page, "03-signup.png")

        # 3. Create a demo customer, sign in, and add an item to the cart.
        page.fill('input[name="username"]', "demo_customer")
        page.fill('input[name="phone"]', "9000000000")
        page.fill('textarea[name="address"]', "12 MG Road, Bengaluru")
        page.fill('input[name="password"]', "StrongDemoPass2026!")
        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/login/**")

        page.fill('input[name="username"]', "demo_customer")
        page.fill('input[name="password"]', "StrongDemoPass2026!")
        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/")

        add_button = page.locator(".add-cart-form button").first
        if add_button.count():
            add_button.click()
            page.wait_for_load_state("load")
            page.locator("[data-open-cart]").click()
            capture(page, "04-cart.png")

        browser.close()


if __name__ == "__main__":
    main()
