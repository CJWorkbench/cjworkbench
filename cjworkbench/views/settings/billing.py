from typing import Any, Dict

from allauth.account.utils import user_display
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.template.response import TemplateResponse

from cjworkbench.models.price import Price
from cjworkbench.models.product import Product
from cjworkbench.models.subscription import Subscription

User = get_user_model()


def jsonize_product(product: Product):
    return {
        "name": product.stripe_product_name,
    }


def jsonize_price(price: Price) -> Dict[str, Any]:
    return {
        "stripePriceId": price.stripe_price_id,
        "product": jsonize_product(price.product),
        "amount": price.stripe_amount,
        "currency": price.stripe_currency,
        "interval": price.stripe_interval,
    }


def jsonize_subscription(subscription: Subscription) -> Dict[str, Any]:
    return {
        "stripeSubscriptionId": subscription.stripe_subscription_id,
        "price": jsonize_price(subscription.price),
        "stripeStatus": subscription.stripe_status,
        "createdAt": subscription.created_at,
        "renewedAt": subscription.renewed_at,
    }


def jsonize_user(user: User) -> Dict[str, Any]:
    return {
        "username": user.username,
        "display_name": user_display(user),
        "stripeCustomerId": user.user_profile.stripe_customer_id,
        "subscriptions": [
            jsonize_subscription(sub)
            for sub in user.subscriptions.select_related(
                "price", "price__product"
            ).all()
        ],
    }


@login_required
def get(request: HttpRequest):
    """Display the billing React app."""
    init_state = {"user": jsonize_user(request.user)}
    return TemplateResponse(request, "settings/billing.html", {"initState": init_state})
