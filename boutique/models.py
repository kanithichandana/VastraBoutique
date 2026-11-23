"""Database models for the Vastra boutique storefront.

Only three things need to persist for the customer experience:

* the dress catalogue (``Dress``),
* customer accounts (``CustomerAccount``), and
* each customer's cart (``CartItem``).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import (
    FileExtensionValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import Q

from .constants import Category, Size
from .utils import next_code

POSITIVE_MONEY = MinValueValidator(
    Decimal("0.01"), message="Enter a valid positive value."
)
MOBILE_VALIDATOR = RegexValidator(
    regex=r"^[0-9]{10,15}$",
    message="Please enter a valid mobile number.",
)


class CodeSequence(models.Model):
    """Locks document numbering so concurrent requests cannot collide."""

    prefix = models.CharField(max_length=10, unique=True)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Code sequence"
        verbose_name_plural = "Code sequences"

    def __str__(self) -> str:
        return f"{self.prefix} ({self.last_value})"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Dress(TimeStampedModel):
    code = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=Category.choices)
    size = models.CharField(max_length=20, choices=Size.choices)
    color = models.CharField(max_length=50)
    fabric = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[POSITIVE_MONEY]
    )
    quantity = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="dresses/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(price__gte=Decimal("0.01")),
                name="dress_price_positive",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=0),
                name="dress_quantity_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    def save(self, *args, **kwargs) -> None:
        if not self.code:
            self.code = next_code("DRS")
        super().save(*args, **kwargs)

    @property
    def is_available(self) -> bool:
        return self.is_active and self.quantity > 0


class CustomerAccountManager(models.Manager):
    def create_account(self, *, username, phone, address, password):
        """Create an account with a hashed password."""
        account = self.model(
            username=str(username).strip().lower(),
            phone=str(phone).strip(),
            address=str(address).strip(),
        )
        account.set_password(password)
        account.save()
        return account


class CustomerAccount(TimeStampedModel):
    """A storefront customer. Kept separate from Django's staff/admin users."""

    username = models.CharField(max_length=50, unique=True)
    phone = models.CharField(
        max_length=15, unique=True, validators=[MOBILE_VALIDATOR]
    )
    address = models.TextField()
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = CustomerAccountManager()

    class Meta:
        ordering = ["username"]
        verbose_name = "Customer account"
        verbose_name_plural = "Customer accounts"

    def __str__(self) -> str:
        return self.username

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)


class CartItem(models.Model):
    customer = models.ForeignKey(
        CustomerAccount, on_delete=models.CASCADE, related_name="cart_items"
    )
    dress = models.ForeignKey(
        Dress, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "dress"],
                name="unique_cart_dress_per_customer",
            )
        ]

    def __str__(self) -> str:
        return f"{self.customer.username} — {self.dress.name} × {self.quantity}"

    @property
    def line_total(self) -> Decimal:
        return self.dress.price * self.quantity
