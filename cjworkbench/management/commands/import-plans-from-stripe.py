from typing import Tuple

import stripe
from django.conf import settings
from django.core.management.base import BaseCommand

from cjworkbench.models.price import Price
from cjworkbench.models.product import Product


def upsert_stripe_product(stripe_product: stripe.Product) -> Tuple[Product, bool]:
    """Upsert Product from Stripe data; return (product, is_created)."""
    return Product.objects.update_or_create(
        stripe_product_id=stripe_product.id,
        defaults={  # Django nit: "defaults" here means, "overwrite"
            **stripe_product.metadata,
            **dict(
                # Override product.metadata, if need be
                stripe_product_name=stripe_product.name
            ),
        },
    )


def upsert_stripe_price(
    product: Product, stripe_price: stripe.Price
) -> Tuple[Price, bool]:
    """Upsert Price from Stripe data; return (price, is_created)."""
    return product.prices.update_or_create(
        stripe_price_id=stripe_price.id,
        defaults=dict(
            # Django nit: "defaults" here means, "overwrite"
            stripe_amount=stripe_price.unit_amount,
            stripe_currency=stripe_price.currency,
            stripe_interval=stripe_price.recurring.interval,
            stripe_active=stripe_price.active,
        ),
    )


class Command(BaseCommand):
    help = "Sync prices from Stripe."

    def handle(self, *args, **options):
        stripe_prices = stripe.Price.list(
            expand=["data.product"], api_key=settings.STRIPE_API_KEY
        )

        db_products = {}  # stripe_product.id => Product

        for stripe_price in stripe_prices.data:
            stripe_product = stripe_price.product
            self.stderr.write(
                f"Syncing Stripe Price {stripe_price.id} ({stripe_product.id} - {stripe_product.name})..."
            )

            try:
                db_product = db_products[stripe_product.id]
            except KeyError:
                db_product, created = upsert_stripe_product(stripe_product)
                db_products[db_product.stripe_product_id] = db_product
                if created:
                    self.stderr.write(f"Created Product {stripe_product.id}")
                else:
                    self.stderr.write(f"Updated Product {stripe_product.id}")

            _, created = upsert_stripe_price(db_product, stripe_price)
            if created:
                self.stderr.write(f"Created Price {stripe_price.id}")
            else:
                self.stderr.write(f"Updated Price {stripe_price.id}")

        for db_price in Price.objects.exclude(
            stripe_price_id__in=list(
                stripe_price.id for stripe_price in stripe_prices.data
            )
        ):
            raise RuntimeError(
                f"Oh, no! Someone deleted a Price on Stripe, {db_price.stripe_price_id}. Please ask a developer to resolve this issue immediately."
            )

        for db_product in Product.objects.exclude(
            stripe_product_id__in=list(db_products.keys())
        ):
            raise RuntimeError(
                f"Oh, no! Someone deleted a Product on Stripe, {db_product.stripe_product_id}. Please ask a developer to resolve this issue immediately."
            )
