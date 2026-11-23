"""Storefront, customer account and cart views."""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .constants import Category
from .forms import CustomerLoginForm, CustomerSignupForm
from .models import CartItem, CustomerAccount, Dress

SESSION_KEY = "vastra_customer_id"

CATEGORY_TILES = [
    (Category.SAREE, "Sarees", "boutique/img/categories/saree.jpg"),
    (Category.KURTA, "Kurta", "boutique/img/categories/kurta.jpg"),
    (Category.LEHENGA, "Lehenga", "boutique/img/categories/lehenga.jpg"),
    (Category.DUPATTA, "Dupatta", "boutique/img/categories/dupatta.jpg"),
    (Category.GOWN, "Gowns", "boutique/img/categories/gown.jpg"),
    (Category.SALWAR_SUIT, "Salwar suit", "boutique/img/categories/salwar-suit.jpg"),
    (Category.OTHER, "More", "boutique/img/categories/more.jpg"),
]


def _current_customer(request) -> CustomerAccount | None:
    customer_id = request.session.get(SESSION_KEY)
    if not customer_id:
        return None
    customer = CustomerAccount.objects.filter(pk=customer_id).first()
    if customer is None:
        request.session.pop(SESSION_KEY, None)
    return customer


def _safe_next(request) -> str:
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ""


def _cart_context(customer: CustomerAccount | None) -> dict:
    if customer is None:
        return {"cart_items": [], "cart_total": Decimal("0.00"), "cart_count": 0}

    items = list(customer.cart_items.select_related("dress"))
    return {
        "cart_items": items,
        "cart_total": sum((item.line_total for item in items), Decimal("0.00")),
        "cart_count": sum(item.quantity for item in items),
    }


def _category_values_for_query(query: str) -> list[str]:
    """Category values whose name matches the term (e.g. 'sarees' -> SAREE)."""
    if len(query) < 2:
        return []
    needle = query.casefold()
    labels = dict(Category.choices)
    values = []
    for value, tile_label, _image in CATEGORY_TILES:
        candidates = (value, tile_label, labels.get(value, ""))
        if any(needle in text.casefold() for text in candidates):
            values.append(value)
    return values


def _group_by_category(dresses: list[Dress]) -> list[dict]:
    """Group matching dresses into labelled category sections in tile order."""
    labels = dict(Category.choices)
    groups = []
    for value, _tile_label, _image in CATEGORY_TILES:
        items = [dress for dress in dresses if dress.category == value]
        if items:
            groups.append(
                {"label": labels.get(value, value), "dresses": items}
            )
    grouped_values = {
        value for value, _label, _image in CATEGORY_TILES
        if any(dress.category == value for dress in dresses)
    }
    for dress in dresses:
        if dress.category not in grouped_values:
            grouped_values.add(dress.category)
            groups.append(
                {
                    "label": dress.get_category_display(),
                    "dresses": [d for d in dresses if d.category == dress.category],
                }
            )
    return groups


def storefront(request):
    """Public one-page catalogue with the signed-in customer's cart."""
    category = request.GET.get("category", "")
    if category and category not in dict(Category.choices):
        category = ""

    query = request.GET.get("q", "").strip()
    matched_categories = _category_values_for_query(query)

    dresses = Dress.objects.filter(is_active=True)
    if category:
        dresses = dresses.filter(category=category)
    if query:
        search = (
            Q(name__icontains=query)
            | Q(code__icontains=query)
            | Q(category__icontains=query)
            | Q(color__icontains=query)
            | Q(fabric__icontains=query)
            | Q(description__icontains=query)
        )
        if matched_categories:
            search |= Q(category__in=matched_categories)
        dresses = dresses.filter(search)

    matched = list(dresses[:12])
    group_by_category = bool(matched_categories)
    customer = _current_customer(request)
    context = {
        "dresses": matched,
        "category_groups": _group_by_category(matched) if group_by_category else [],
        "group_by_category": group_by_category,
        "categories": [
            {"value": value, "label": label, "image": image}
            for value, label, image in CATEGORY_TILES
        ],
        "active_category": category,
        "search_query": query,
        "customer": customer,
        "contact": settings.STOREFRONT_CONTACT,
    }
    context.update(_cart_context(customer))
    return render(request, "boutique/storefront.html", context)


def signup(request):
    if _current_customer(request) is not None:
        return redirect("boutique:storefront")

    next_url = _safe_next(request)
    if request.method == "POST":
        form = CustomerSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Your account is ready. Please sign in to continue."
            )
            target = reverse("boutique:login")
            if next_url:
                target = f"{target}?{urlencode({'next': next_url})}"
            return redirect(target)
    else:
        form = CustomerSignupForm()

    return render(
        request,
        "registration/signup.html",
        {"form": form, "next": next_url},
    )


def login_view(request):
    next_url = _safe_next(request)
    if _current_customer(request) is not None:
        return redirect(next_url or "boutique:storefront")

    if request.method == "POST":
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            customer = form.customer
            request.session[SESSION_KEY] = customer.pk
            request.session.modified = True
            CustomerAccount.objects.filter(pk=customer.pk).update(
                last_login=timezone.now()
            )
            messages.success(request, f"Welcome back, {customer.username}.")
            return redirect(next_url or "boutique:storefront")
    else:
        form = CustomerLoginForm()

    return render(
        request,
        "registration/login.html",
        {"form": form, "next": next_url},
    )


@require_POST
def logout_view(request):
    request.session.pop(SESSION_KEY, None)
    messages.info(request, "You have been signed out.")
    return redirect("boutique:storefront")


@require_POST
def cart_add(request, pk: int):
    customer = _current_customer(request)
    if customer is None:
        target = reverse("boutique:storefront")
        return redirect(
            f"{reverse('boutique:login')}?{urlencode({'next': target})}"
        )

    dress = Dress.objects.filter(pk=pk, is_active=True).first()
    if dress is None:
        raise Http404("Dress not found.")

    if dress.quantity < 1:
        messages.error(request, "This dress is currently unavailable.")
        return redirect("boutique:storefront")

    item, _ = CartItem.objects.get_or_create(
        customer=customer, dress=dress, defaults={"quantity": 0}
    )
    if item.quantity >= dress.quantity:
        messages.error(
            request,
            f"Only {dress.quantity} available in stock for {dress.name}.",
        )
    else:
        item.quantity += 1
        item.save(update_fields=["quantity"])
        messages.success(request, f"{dress.name} added to your cart.")
    return redirect("boutique:storefront")


@require_POST
def cart_remove(request, pk: int):
    customer = _current_customer(request)
    if customer is None:
        target = reverse("boutique:storefront")
        return redirect(
            f"{reverse('boutique:login')}?{urlencode({'next': target})}"
        )

    deleted, _ = CartItem.objects.filter(customer=customer, dress_id=pk).delete()
    if deleted:
        messages.info(request, "Item removed from your cart.")
    return redirect("boutique:storefront")
