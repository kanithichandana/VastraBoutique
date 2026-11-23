"""Shared catalogue choices."""

from django.db import models


class Category(models.TextChoices):
    SAREE = "SAREE", "Saree"
    KURTA = "KURTA", "Kurta / Kurti"
    LEHENGA = "LEHENGA", "Lehenga"
    SALWAR_SUIT = "SALWAR_SUIT", "Salwar Suit"
    DUPATTA = "DUPATTA", "Dupatta"
    GOWN = "GOWN", "Gown"
    OTHER = "OTHER", "Other"


class Size(models.TextChoices):
    XS = "XS", "XS"
    S = "S", "S"
    M = "M", "M"
    L = "L", "L"
    XL = "XL", "XL"
    XXL = "XXL", "XXL"
    FREE = "FREE", "Free Size"
