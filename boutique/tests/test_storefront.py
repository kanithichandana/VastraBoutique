"""Tests for the customer-only Vastra storefront."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from boutique.models import CartItem, CustomerAccount, Dress


def make_dress(
    name="Test Saree", *, category="SAREE", color="Maroon", price="1000.00", quantity=5
):
    return Dress.objects.create(
        name=name,
        category=category,
        size="FREE",
        color=color,
        fabric="Silk",
        price=price,
        quantity=quantity,
    )


SIGNUP_DATA = {
    "username": "ananya",
    "phone": "9876543210",
    "address": "12 MG Road, Bengaluru",
    "password": "Str0ngPass!2026",
}


class StorefrontTests(TestCase):
    def test_storefront_is_public_and_contains_required_sections(self):
        make_dress("Kanjivaram Saree")

        response = self.client.get(reverse("boutique:storefront"))

        self.assertEqual(response.status_code, 200)
        for text in [
            "Vastra",
            "Categories",
            "Sign in",
            "Create account",
            "Add to cart",
            "Products",
            "hello@vastra.example.com",
            "Bengaluru",
        ]:
            self.assertContains(response, text)
        self.assertContains(response, "Kanjivaram Saree")

    def test_category_filter_limits_products(self):
        make_dress("Banarasi Saree", category="SAREE")
        make_dress("Cotton Kurta", category="KURTA")

        response = self.client.get(reverse("boutique:storefront"), {"category": "KURTA"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cotton Kurta")
        self.assertNotContains(response, "Banarasi Saree")

    def test_invalid_category_is_ignored(self):
        make_dress("Banarasi Saree")
        response = self.client.get(reverse("boutique:storefront"), {"category": "NOPE"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Banarasi Saree")

    def test_header_search_filters_by_name_and_colour(self):
        make_dress("Banarasi Saree", color="Maroon")
        make_dress("Cotton Kurta", category="KURTA", color="Indigo")

        by_name = self.client.get(reverse("boutique:storefront"), {"q": "kurta"})
        self.assertContains(by_name, "Cotton Kurta")
        self.assertNotContains(by_name, "Banarasi Saree")
        self.assertContains(by_name, "Results for “kurta”")

        by_colour = self.client.get(reverse("boutique:storefront"), {"q": "maroon"})
        self.assertContains(by_colour, "Banarasi Saree")
        self.assertNotContains(by_colour, "Cotton Kurta")

    def test_search_is_combined_with_active_category(self):
        make_dress("Banarasi Saree", category="SAREE", color="Maroon")
        make_dress("Cotton Kurta", category="KURTA", color="Maroon")

        response = self.client.get(
            reverse("boutique:storefront"), {"category": "SAREE", "q": "maroon"}
        )
        self.assertContains(response, "Banarasi Saree")
        self.assertNotContains(response, "Cotton Kurta")

    def test_search_with_no_matches_shows_empty_message(self):
        make_dress("Banarasi Saree")
        response = self.client.get(reverse("boutique:storefront"), {"q": "no-match"})
        self.assertContains(response, "No products match your search")

    def test_category_name_search_groups_products_by_category(self):
        make_dress("Banarasi Silk Saree", category="SAREE")
        make_dress("Kanjivaram Saree", category="SAREE")
        make_dress("Chikankari Kurta", category="KURTA")

        response = self.client.get(reverse("boutique:storefront"), {"q": "saree"})

        self.assertContains(response, "Results for “saree”")
        self.assertContains(response, "category-group")
        self.assertContains(response, ">Saree<")
        self.assertContains(response, "2 items")
        self.assertNotContains(response, "Chikankari Kurta")

    def test_plural_category_search_also_groups(self):
        make_dress("Banarasi Silk Saree", category="SAREE")
        response = self.client.get(reverse("boutique:storefront"), {"q": "sarees"})
        self.assertContains(response, "category-group")
        self.assertContains(response, "Banarasi Silk Saree")

    def test_fabric_search_stays_as_flat_grid(self):
        make_dress("Banarasi Silk Saree", category="SAREE")
        response = self.client.get(reverse("boutique:storefront"), {"q": "silk"})
        self.assertNotContains(response, "category-group")
        self.assertContains(response, "Banarasi Silk Saree")


class SignupTests(TestCase):
    def test_signup_creates_account_with_hashed_password_and_redirects_to_login(self):
        response = self.client.post(reverse("boutique:signup"), SIGNUP_DATA)

        self.assertRedirects(response, reverse("boutique:login"))
        account = CustomerAccount.objects.get(username="ananya")
        self.assertEqual(account.phone, "9876543210")
        self.assertEqual(account.address, "12 MG Road, Bengaluru")
        self.assertNotEqual(account.password, SIGNUP_DATA["password"])
        self.assertTrue(account.check_password(SIGNUP_DATA["password"]))
        # Sign-up must not log the customer in.
        self.assertNotIn("vastra_customer_id", self.client.session)

    def test_signup_normalises_username(self):
        data = dict(SIGNUP_DATA, username="  AnAnYa  ")
        self.client.post(reverse("boutique:signup"), data)
        self.assertTrue(CustomerAccount.objects.filter(username="ananya").exists())

    def test_signup_rejects_duplicate_username_and_phone(self):
        self.client.post(reverse("boutique:signup"), SIGNUP_DATA)
        response = self.client.post(reverse("boutique:signup"), SIGNUP_DATA)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already taken")

        other = dict(SIGNUP_DATA, username="meera")
        response = self.client.post(reverse("boutique:signup"), other)
        self.assertContains(response, "already exists")

    def test_signup_requires_all_fields(self):
        response = self.client.post(reverse("boutique:signup"), {})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        for field in ["username", "phone", "address", "password"]:
            self.assertIn(field, form.errors)


class LoginTests(TestCase):
    def setUp(self):
        self.client.post(reverse("boutique:signup"), SIGNUP_DATA)

    def test_login_with_correct_credentials_goes_to_storefront(self):
        response = self.client.post(
            reverse("boutique:login"),
            {"username": "ananya", "password": SIGNUP_DATA["password"]},
        )
        self.assertRedirects(response, reverse("boutique:storefront"))
        self.assertEqual(
            self.client.session["vastra_customer_id"],
            CustomerAccount.objects.get(username="ananya").pk,
        )

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            reverse("boutique:login"),
            {"username": "ananya", "password": "wrongpass"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incorrect username or password")
        self.assertNotIn("vastra_customer_id", self.client.session)

    def test_login_accepts_case_insensitive_username(self):
        response = self.client.post(
            reverse("boutique:login"),
            {"username": "ANANYA", "password": SIGNUP_DATA["password"]},
        )
        self.assertRedirects(response, reverse("boutique:storefront"))

    def test_logout_clears_session(self):
        self.client.post(
            reverse("boutique:login"),
            {"username": "ananya", "password": SIGNUP_DATA["password"]},
        )
        response = self.client.post(reverse("boutique:logout"))
        self.assertRedirects(response, reverse("boutique:storefront"))
        self.assertNotIn("vastra_customer_id", self.client.session)

    def test_safe_next_is_honoured(self):
        target = reverse("boutique:storefront") + "?category=KURTA"
        response = self.client.post(
            reverse("boutique:login"),
            {"username": "ananya", "password": SIGNUP_DATA["password"], "next": target},
        )
        self.assertRedirects(response, target)

    def test_unsafe_next_is_ignored(self):
        response = self.client.post(
            reverse("boutique:login"),
            {
                "username": "ananya",
                "password": SIGNUP_DATA["password"],
                "next": "https://evil.example.com/",
            },
        )
        self.assertRedirects(response, reverse("boutique:storefront"))


class CartTests(TestCase):
    def setUp(self):
        self.dress = make_dress("Velvet Lehenga", price="12500.00", quantity=2)
        self.client.post(reverse("boutique:signup"), SIGNUP_DATA)
        self.client.post(
            reverse("boutique:login"),
            {"username": "ananya", "password": SIGNUP_DATA["password"]},
        )
        self.customer = CustomerAccount.objects.get(username="ananya")

    def test_add_to_cart_creates_and_increments_item(self):
        url = reverse("boutique:cart_add", args=[self.dress.pk])
        self.client.post(url)
        self.client.post(url)

        item = CartItem.objects.get(customer=self.customer, dress=self.dress)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.line_total, Decimal("25000.00"))

        response = self.client.get(reverse("boutique:storefront"))
        self.assertContains(response, "Velvet Lehenga")
        self.assertContains(response, "25000.00")

    def test_add_to_cart_respects_stock(self):
        url = reverse("boutique:cart_add", args=[self.dress.pk])
        self.client.post(url)
        self.client.post(url)
        response = self.client.post(url, follow=True)

        item = CartItem.objects.get(customer=self.customer, dress=self.dress)
        self.assertEqual(item.quantity, 2)
        self.assertContains(response, "Only 2 available in stock")

    def test_remove_from_cart(self):
        url = reverse("boutique:cart_remove", args=[self.dress.pk])
        self.client.post(reverse("boutique:cart_add", args=[self.dress.pk]))
        response = self.client.post(url)

        self.assertRedirects(response, reverse("boutique:storefront"))
        self.assertFalse(CartItem.objects.filter(customer=self.customer).exists())

    def test_cart_requires_login(self):
        self.client.post(reverse("boutique:logout"))
        response = self.client.post(reverse("boutique:cart_add", args=[self.dress.pk]))
        self.assertRedirects(
            response,
            reverse("boutique:login") + "?next=" + reverse("boutique:storefront"),
        )

    def test_carts_are_isolated_per_account(self):
        self.client.post(reverse("boutique:cart_add", args=[self.dress.pk]))

        # Create a second customer directly (signup redirects logged-in users).
        CustomerAccount.objects.create_account(
            username="meera",
            phone="9876543211",
            address="42 Boat Club Road, Chennai",
            password=SIGNUP_DATA["password"],
        )
        self.client.post(reverse("boutique:logout"))
        self.client.post(
            reverse("boutique:login"),
            {"username": "meera", "password": SIGNUP_DATA["password"]},
        )
        response = self.client.get(reverse("boutique:storefront"))

        self.assertContains(response, "Your cart is empty")
        self.assertEqual(CartItem.objects.filter(customer__username="meera").count(), 0)
        self.assertEqual(CartItem.objects.filter(customer__username="ananya").count(), 1)

    def test_cart_get_is_not_allowed(self):
        response = self.client.get(reverse("boutique:cart_add", args=[self.dress.pk]))
        self.assertEqual(response.status_code, 405)
