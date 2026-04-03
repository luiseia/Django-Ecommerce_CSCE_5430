from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("products", "0002_remove_product_stock_inventory_review"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductViewEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("view_count", models.PositiveIntegerField(default=1)),
                ("last_viewed_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="view_events", to="products.product")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_view_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-last_viewed_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="productviewevent",
            constraint=models.UniqueConstraint(fields=("user", "product"), name="unique_user_product_view_event"),
        ),
    ]
