from typing import Any, Dict

from allauth.account.utils import user_display
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.template.response import TemplateResponse

from cjworkbench.models import Plan, Subscription

User = get_user_model()


def jsonize_plan(plan: Plan) -> Dict[str, Any]:
    return {
        "stripePriceId": plan.stripe_price_id,
        "name": plan.stripe_product_name,
        "amount": plan.stripe_amount,
        "currency": plan.stripe_currency,
    }


def jsonize_subscription(subscription: Subscription) -> Dict[str, Any]:
    return {
        "stripeSubscriptionId": subscription.stripe_subscription_id,
        "plan": jsonize_plan(subscription.plan),
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
            for sub in user.subscriptions.select_related("plan").all()
        ],
    }


@login_required
def get(request: HttpRequest):
    """Display the billing React app."""
    init_state = {"user": jsonize_user(request.user)}
    return TemplateResponse(request, "settings/billing.html", {"initState": init_state})
