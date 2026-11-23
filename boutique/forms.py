"""Storefront forms. All user input is validated server-side."""

from __future__ import annotations

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import CustomerAccount


def _style_fields(form: forms.BaseForm) -> None:
    """Apply a consistent CSS class to every widget in a form."""
    for field in form.fields.values():
        widget = field.widget
        current = widget.attrs.get("class", "")
        if isinstance(widget, (forms.Select, forms.SelectMultiple)):
            widget.attrs["class"] = f"{current} form-select".strip()
        else:
            widget.attrs["class"] = f"{current} form-control".strip()


class CustomerSignupForm(forms.ModelForm):
    """Create a storefront account with a securely hashed password."""

    password = forms.CharField(
        min_length=8,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = CustomerAccount
        fields = ["username", "phone", "address"]
        widgets = {
            "address": forms.Textarea(
                attrs={"rows": 3, "placeholder": "House / street, city, PIN"}
            ),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        _style_fields(self)
        self.fields["username"].widget.attrs.update(
            {
                "placeholder": "Choose a username",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
        self.fields["phone"].widget.attrs.update(
            {"placeholder": "10-digit mobile number", "autocomplete": "tel"}
        )
        self.fields["password"].widget.attrs["placeholder"] = "At least 8 characters"

    def clean_username(self) -> str:
        username = self.cleaned_data["username"].strip().lower()
        if len(username) < 3:
            raise ValidationError("Choose a username with at least 3 characters.")
        if CustomerAccount.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_phone(self) -> str:
        phone = "".join(
            ch for ch in str(self.cleaned_data["phone"]) if ch.isdigit() or ch == "+"
        )
        if CustomerAccount.objects.filter(phone=phone).exists():
            raise ValidationError("An account with this phone number already exists.")
        return phone

    def clean_address(self) -> str:
        address = self.cleaned_data["address"].strip()
        if len(address) < 5:
            raise ValidationError("Please enter your full address.")
        return address

    def clean_password(self) -> str:
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self, commit: bool = True) -> CustomerAccount:
        account = super().save(commit=False)
        account.set_password(self.cleaned_data["password"])
        if commit:
            account.save()
        return account


class CustomerLoginForm(forms.Form):
    """Validate a storefront account without touching Django's auth users."""

    username = forms.CharField(max_length=50)
    password = forms.CharField(strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        _style_fields(self)
        self.fields["username"].widget.attrs.update(
            {"placeholder": "Username", "autocomplete": "username", "autofocus": True}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "Password", "autocomplete": "current-password"}
        )
        self.customer: CustomerAccount | None = None

    def clean(self):
        cleaned_data = super().clean()
        username = str(cleaned_data.get("username", "")).strip().lower()
        password = cleaned_data.get("password")

        if username and password:
            customer = CustomerAccount.objects.filter(username=username).first()
            if customer is None or not customer.check_password(password):
                raise ValidationError("Incorrect username or password.")
            self.customer = customer
        return cleaned_data
