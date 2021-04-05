import itertools
from typing import Any, Dict, Iterable, List

from allauth.account.utils import user_display
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.template.response import TemplateResponse

from cjworkbench.models.price import Price
from cjworkbench.models.product import Product
from cjworkbench.models.subscription import Subscription
from cjworkbench.models.userlimits import UserLimits

User = get_user_model()


FREE_PRODUCT = Product(
    stripe_product_id=None,
    stripe_product_name="Free Plan",
    **UserLimits()._asdict(),
)


def jsonize_user(user: User) -> Dict[str, Any]:
    if user.is_anonymous:
        return None

    stripe_customer_id = user.user_profile.stripe_customer_id
    subscribed_stripe_product_ids = list(
        user.subscriptions.select_related("price__product").values_list(
            "price__product__stripe_product_id", flat=True
        )
    )

    return {
        "username": user.username,
        "display_name": user_display(user),
        "subscribedStripeProductIds": subscribed_stripe_product_ids,
        "stripeCustomerId": stripe_customer_id,
    }


def jsonize_price(price: Price) -> Dict[str, Any]:
    return {
        "stripePriceId": price.stripe_price_id,
        "amount": price.stripe_amount,  # in cents
        "currency": price.stripe_currency,  # e.g., "usd"
        "interval": price.stripe_interval,  # "month" or "year"
    }


def jsonize_product(product: Product, prices: Iterable[Price]) -> Dict[str, Any]:
    return {
        "stripeProductId": product.stripe_product_id,
        "name": product.stripe_product_name,
        "maxFetchesPerDay": product.max_fetches_per_day,
        "maxDeltaAgeInDays": product.max_delta_age_in_days,
        "canCreateSecretLink": product.can_create_secret_link,
        "prices": [jsonize_price(price) for price in prices],
    }


def jsonize_products() -> List[Dict[str, Any]]:
    # One SQL query. Query for Prices that are active, and group by Product.
    #
    # Order prices within a Product by stripe_amount, assuming cheaper means
    # shorter timespan.
    prices = list(
        Price.objects.filter(stripe_active=True)
        .select_related("product")
        .order_by("product__stripe_product_name", "stripe_amount")
    )

    product_prices = {}  # product => [price1, price2, ...]
    for price in prices:
        product_prices.setdefault(price.product, []).append(price)

    return [
        jsonize_product(FREE_PRODUCT, []),
        *(
            jsonize_product(product, prices)
            for product, prices in product_prices.items()
        ),
    ]


def get(request: HttpRequest):
    """Display the billing React app."""
    init_state = {
        "user": jsonize_user(request.user),
        "products": jsonize_products(),
    }
    return TemplateResponse(request, "settings/plan.html", {"initState": init_state})
