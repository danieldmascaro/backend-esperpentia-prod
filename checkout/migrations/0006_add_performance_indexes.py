import checkout.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checkout", "0005_repair_legacy_cartitem_book_fk"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="cartitem",
            index=models.Index(fields=["cart", "book"], name="idx_cartitem_cart_book"),
        ),
        migrations.AddIndex(
            model_name="cartitem",
            index=models.Index(fields=["cart", "-updated_at"], name="idx_cartitem_cart_updated"),
        ),
        migrations.AlterField(
            model_name="cartdiscount",
            name="code",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="cartdiscount",
            name="type",
            field=models.CharField(
                choices=[
                    ("coupon", "Coupon"),
                    ("percent", "Percent"),
                    ("fixed", "Fixed"),
                    ("qty_promo", "Quantity promo"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="cartdiscount",
            index=models.Index(fields=["cart", "-created_at"], name="idx_cartdiscount_cart_created"),
        ),
        migrations.AlterField(
            model_name="carttaxline",
            name="name",
            field=models.CharField(db_index=True, max_length=120),
        ),
        migrations.AddIndex(
            model_name="carttaxline",
            index=models.Index(fields=["cart", "name"], name="idx_carttaxline_cart_name"),
        ),
        migrations.AlterField(
            model_name="cartoperationlog",
            name="operation",
            field=models.CharField(db_index=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="cartoperationlog",
            name="expires_at",
            field=models.DateTimeField(db_index=True, default=checkout.models.default_cart_expiry),
        ),
        migrations.AddIndex(
            model_name="cartoperationlog",
            index=models.Index(fields=["expires_at"], name="idx_opslog_expires"),
        ),
    ]
