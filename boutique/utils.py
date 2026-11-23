"""Small, reusable helpers for Vastra."""

from __future__ import annotations

from django.db import IntegrityError, transaction


def next_code(prefix: str, width: int = 6) -> str:
    """Return the next human-friendly catalogue code (e.g. ``DRS-000001``).

    The sequence row is locked so simultaneous requests cannot issue the same
    identifier, on MySQL or SQLite.
    """

    # Imported lazily to keep the models -> utils -> models import graph acyclic.
    from .models import CodeSequence

    for _ in range(3):
        try:
            with transaction.atomic():
                sequence, _ = CodeSequence.objects.select_for_update().get_or_create(
                    prefix=prefix
                )
                sequence.last_value += 1
                sequence.save(update_fields=["last_value"])
                return f"{prefix}-{sequence.last_value:0{width}d}"
        except IntegrityError:
            # Another request created the sequence row at the same time.
            continue
    raise RuntimeError(f"Could not allocate a code for prefix {prefix!r}.")
