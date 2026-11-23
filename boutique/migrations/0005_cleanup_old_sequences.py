"""Remove code-sequence counters left behind by deleted modules."""

from django.db import migrations


def cleanup(apps, schema_editor):
    CodeSequence = apps.get_model("boutique", "CodeSequence")
    # Only the dress catalogue issues codes now; CUS/BOK/BIL belonged to the
    # removed customer, booking and bill modules.
    CodeSequence.objects.exclude(prefix="DRS").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("boutique", "0004_customer_only_storefront"),
    ]

    operations = [
        migrations.RunPython(cleanup, migrations.RunPython.noop),
    ]
