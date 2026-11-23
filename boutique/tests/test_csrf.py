"""CSRF-enforced tests for every state-changing storefront endpoint.

Django's default test client skips CSRF checks, so the original suite could pass
even if a form lost its token. These tests use ``enforce_csrf_checks=True`` to
verify both that missing tokens are rejected and that the rendered forms supply
valid tokens for every real POST route.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from boutique.models import CartItem, CustomerAccount, Dress

PASSWORD = "Str0ngPass!2026"
TOKEN_RE = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')


class CsrfEnforcedTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.account = CustomerAccount.objects.create_account(
            username="csrfuser",
            phone="9000000003",
            address="3 CSRF Lane, Bengaluru",
            password=PASSWORD,
        )
        self.dress = Dress.objects.create(
            name="CSRF Test Saree",
            category="SAREE",
            size="FREE",
            color="Maroon",
            fabric="Silk",
            price="1000.00",
            quantity=5,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def token_from(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f"Cannot load {url} for CSRF token")
        match = TOKEN_RE.search(response.content.decode())
        self.assertIsNotNone(match, f"No CSRF token rendered on {url}")
        return match.group(1)

    def login(self):
        response = self.client.post(
            reverse("boutique:login"),
            {
                "username": "csrfuser",
                "password": PASSWORD,
                "csrfmiddlewaretoken": self.token_from(reverse("boutique:login")),
            },
        )
        self.assertRedirects(response, reverse("boutique:storefront"))

    def post_with_token(self, source_url, target_url, data=None):
        payload = dict(data or {})
        payload["csrfmiddlewaretoken"] = self.token_from(source_url)
        return self.client.post(target_url, payload)

    # ------------------------------------------------------------------
    # Sign up
    # ------------------------------------------------------------------
    def test_signup_without_token_is_forbidden(self):
        response = self.client.post(
            reverse("boutique:signup"),
            {
                "username": "csrfnewuser",
                "phone": "9000000004",
                "address": "4 CSRF Lane",
                "password": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CustomerAccount.objects.filter(username="csrfnewuser").exists())

    def test_signup_with_token_succeeds(self):
        response = self.post_with_token(
            reverse("boutique:signup"),
            reverse("boutique:signup"),
            {
                "username": "csrfnewuser",
                "phone": "9000000004",
                "address": "4 CSRF Lane",
                "password": PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("boutique:login"))
        self.assertTrue(CustomerAccount.objects.filter(username="csrfnewuser").exists())

    # ------------------------------------------------------------------
    # Sign in
    # ------------------------------------------------------------------
    def test_login_without_token_is_forbidden(self):
        response = self.client.post(
            reverse("boutique:login"),
            {"username": "csrfuser", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("vastra_customer_id", self.client.session)

    def test_login_with_token_succeeds(self):
        response = self.post_with_token(
            reverse("boutique:login"),
            reverse("boutique:login"),
            {"username": "csrfuser", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("boutique:storefront"))
        self.assertEqual(self.client.session["vastra_customer_id"], self.account.pk)

    # ------------------------------------------------------------------
    # Cart add
    # ------------------------------------------------------------------
    def test_cart_add_without_token_is_forbidden(self):
        self.login()
        url = reverse("boutique:cart_add", args=[self.dress.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CartItem.objects.filter(customer=self.account).exists())

    def test_cart_add_with_token_succeeds(self):
        self.login()
        response = self.post_with_token(
            reverse("boutique:storefront"),
            reverse("boutique:cart_add", args=[self.dress.pk]),
        )
        self.assertRedirects(response, reverse("boutique:storefront"))
        self.assertEqual(CartItem.objects.get(customer=self.account, dress=self.dress).quantity, 1)

    # ------------------------------------------------------------------
    # Cart remove
    # ------------------------------------------------------------------
    def test_cart_remove_without_token_is_forbidden(self):
        self.login()
        CartItem.objects.create(customer=self.account, dress=self.dress, quantity=1)
        response = self.client.post(
            reverse("boutique:cart_remove", args=[self.dress.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(CartItem.objects.filter(customer=self.account).exists())

    def test_cart_remove_with_token_succeeds(self):
        self.login()
        CartItem.objects.create(customer=self.account, dress=self.dress, quantity=1)
        response = self.post_with_token(
            reverse("boutique:storefront"),
            reverse("boutique:cart_remove", args=[self.dress.pk]),
        )
        self.assertRedirects(response, reverse("boutique:storefront"))
        self.assertFalse(CartItem.objects.filter(customer=self.account).exists())

    # ------------------------------------------------------------------
    # Sign out
    # ------------------------------------------------------------------
    def test_logout_without_token_is_forbidden(self):
        self.login()
        response = self.client.post(reverse("boutique:logout"))
        self.assertEqual(response.status_code, 403)
        self.assertIn("vastra_customer_id", self.client.session)

    def test_logout_with_token_succeeds(self):
        self.login()
        response = self.post_with_token(
            reverse("boutique:storefront"), reverse("boutique:logout")
        )
        self.assertRedirects(response, reverse("boutique:storefront"))
        self.assertNotIn("vastra_customer_id", self.client.session)

    # ------------------------------------------------------------------
    # Static template audit
    # ------------------------------------------------------------------
    def test_every_post_form_template_has_csrf_token(self):
        template_root = Path(settings.BASE_DIR) / "boutique" / "templates"
        form_re = re.compile(
            r"<form\b[^>]*\bmethod=[\"']post[\"'][^>]*>(.*?)</form>",
            re.IGNORECASE | re.DOTALL,
        )
        checked = 0
        for path in template_root.rglob("*.html"):
            html = path.read_text(encoding="utf-8")
            for match in form_re.finditer(html):
                checked += 1
                self.assertIn(
                    "{% csrf_token %}",
                    match.group(1),
                    f"POST form in {path.relative_to(settings.BASE_DIR)} is missing a CSRF token",
                )
        self.assertGreaterEqual(checked, 5, "Expected to audit all storefront POST forms")
