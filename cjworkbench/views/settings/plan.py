from typing import Any, Dict

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.template.response import TemplateResponse

from cjworkbench.models import Plan, Subscription
from cjworkbench.models.userlimits import UserLimits

User = get_user_model()


def jsonize_plan(plan: Plan) -> Dict[str, Any]:
    return {
        "stripePriceId": plan.stripe_price_id,
        "name": plan.stripe_product_name,
        "amount": plan.stripe_amount,  # in cents
        "currency": plan.stripe_currency,  # e.g., "usd"
        "maxFetchesPerDay": plan.max_fetches_per_day,
        "maxDeltaAgeInDays": plan.max_delta_age_in_days,
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
    active_plans = [
        jsonize_plan(subscription.plan) for subscription in user.subscriptions.all()
    ]

    return {
        "username": user.username,
        "subscribedPlans": active_plans,
        "stripeCustomerId": user.user_profile.stripe_customer_id,
    }


def jsonize_plans() -> Dict[str, Dict[str, Any]]:
    FreePlan = Plan(
        stripe_price_id=None,  # special case
        stripe_product_name="Free Plan",
        stripe_amount=0,
        stripe_currency="usd",
        **UserLimits()._asdict(),
    )

    return [
        jsonize_plan(FreePlan),
        *(jsonize_plan(plan) for plan in Plan.objects.filter(stripe_active=True)),
    ]


@login_required
def get(request: HttpRequest):
    """Display the billing React app."""
    init_state = {
        "user": jsonize_user(request.user),
        "plans": jsonize_plans(),
    }
    return TemplateResponse(request, "settings/plan.html", {"initState": init_state})
