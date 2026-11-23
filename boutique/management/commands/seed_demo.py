"""Load the Vastra catalogue for a fresh local database.

This command is idempotent: it only creates dresses that are not present yet.
Demo credentials are *not* created here — customers sign up through the site,
and staff/admin users are created with ``python manage.py createsuperuser``.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from boutique.models import Dress


CATALOGUE = [
    {
        "name": "Banarasi Silk Saree",
        "category": "SAREE",
        "size": "FREE",
        "color": "Maroon",
        "fabric": "Pure Silk",
        "price": "12500.00",
        "quantity": 6,
        "description": "Handpicked banarasi silk saree from the Vastra collection.",
    },
    {
        "name": "Kanjivaram Bridal Saree",
        "category": "SAREE",
        "size": "FREE",
        "color": "Antique Gold",
        "fabric": "Silk",
        "price": "24500.00",
        "quantity": 4,
        "description": "Handpicked kanjivaram bridal saree from the Vastra collection.",
    },
    {
        "name": "Chikankari Kurta Set",
        "category": "KURTA",
        "size": "M",
        "color": "Cream",
        "fabric": "Cotton",
        "price": "4200.00",
        "quantity": 2,
        "description": "Handpicked chikankari kurta set from the Vastra collection.",
    },
    {
        "name": "Velvet Lehenga",
        "category": "LEHENGA",
        "size": "L",
        "color": "Wine",
        "fabric": "Velvet",
        "price": "18500.00",
        "quantity": 8,
        "description": "Handpicked velvet lehenga from the Vastra collection.",
    },
    {
        "name": "Hand embroidered Dupatta",
        "category": "DUPATTA",
        "size": "FREE",
        "color": "Ivory",
        "fabric": "Georgette",
        "price": "2800.00",
        "quantity": 5,
        "description": "Handpicked embroidered dupatta from the Vastra collection.",
    },
    {
        "name": "Festive Anarkali Gown",
        "category": "GOWN",
        "size": "S",
        "color": "Emerald",
        "fabric": "Chiffon",
        "price": "9700.00",
        "quantity": 3,
        "description": "Handpicked festive anarkali gown from the Vastra collection.",
    },
    {
        "name": "Kashmiri Pashmina Shawl",
        "category": "OTHER",
        "size": "FREE",
        "color": "Rust",
        "fabric": "Pashmina",
        "price": "15600.00",
        "quantity": 0,
        "description": "Handpicked pashmina shawl from the Vastra collection.",
    },
    {
        "name": "Cotton Salwar Suit",
        "category": "SALWAR_SUIT",
        "size": "XL",
        "color": "Indigo",
        "fabric": "Cotton",
        "price": "3400.00",
        "quantity": 7,
        "description": "Handpicked cotton salwar suit from the Vastra collection.",
    },
]


class Command(BaseCommand):
    help = "Populate the storefront catalogue with demo dresses."

    def handle(self, *args, **options) -> None:
        created = 0
        with transaction.atomic():
            for item in CATALOGUE:
                _, was_created = Dress.objects.get_or_create(
                    name=item["name"], defaults=item
                )
                created += int(was_created)

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Added {created} dress(es) to the catalogue.")
            )
        else:
            self.stdout.write(self.style.WARNING("Catalogue already populated."))
