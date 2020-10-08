from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import stripe

from cjworkbench.models import Plan


class Command(BaseCommand):
    help = "Sync plans from Stripe."

    def handle(self, *args, **options):
        prices = stripe.Price.list(
            expand=["data.product"], api_key=settings.STRIPE_API_KEY
        )
        product_id_to_prices = {}
        skipped_product_ids = set()
        for price in prices.data:
            product = price.product
            if product.id not in product_id_to_prices:
                product_id_to_prices[product.id] = []
            product_id_to_prices[product.id].append(price)

        for product_prices in product_id_to_prices.values():
            price = product_prices[0]
            product = price.product
            self.stderr.write(
                f"Syncing Stripe project {product.id} ({product.name})..."
            )
            plan, created = Plan.upsert_from_stripe_product_and_price(product, price)
            if created:
                self.stderr.write(
                    f"Created Plan {product.id} ({product.name} - {price.id})"
                )
            else:
                self.stderr.write(
                    f"Updated Plan {product.id} ({product.name} - {price.id})"
                )

        for plan in Plan.objects.exclude(
            stripe_product_id__in=list(product_id_to_prices.keys())
        ):
            raise RuntimeError(
                f"Oh, no! Someone deleted a Product on Stripe, {plan.stripe_product_id}. Please ask a developer to resolve this issue immediately."
            )
