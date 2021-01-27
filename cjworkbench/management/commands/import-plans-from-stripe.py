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
        for price in prices.data:
            product = price.product
            self.stderr.write(
                f"Syncing Stripe Price {price.id} ({product.id} - {product.name})..."
            )
            plan, created = Plan.upsert_from_stripe_product_and_price(
                price, price.product
            )
            if created:
                self.stderr.write(f"Created Plan {price.id}")
            else:
                self.stderr.write(f"Updated Plan {price.id}")

        for plan in Plan.objects.exclude(
            stripe_price_id__in=list(price.id for price in prices.data)
        ):
            raise RuntimeError(
                f"Oh, no! Someone deleted a Price on Stripe, {plan.stripe_price_id}. Please ask a developer to resolve this issue immediately."
            )
