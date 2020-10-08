from django.contrib import admin
from cjworkbench.models.userprofile import UserProfile
from cjworkbench.models.plan import Plan


class ReadOnlyModelAdmin(admin.ModelAdmin):
    def has_view_permission(self, *x, **y):
        return True

    def has_delete_permission(self, *x, **y):
        return False

    def has_change_permission(self, *x, **y):
        return False

    def has_add_permission(self, *x, **y):
        return False


class UserProfileAdmin(admin.ModelAdmin):
    ordering = ("user__email",)
    readonly_fields = ("user",)
    search_fields = ("user__email", "user__username")


class PlanAdmin(ReadOnlyModelAdmin):
    """Plans, maintained on Stripe.

    Users may not edit these plans. They must set up Plans using Products on the
    Stripe Dashboard, then call `python ./manage.py import-plans-from-stripe`.
    """

    ordering = ("stripe_product_name",)


admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Plan, PlanAdmin)
