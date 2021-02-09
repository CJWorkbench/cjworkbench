from django.contrib import admin

from cjworkbench.models.price import Price
from cjworkbench.models.product import Product
from cjworkbench.models.userprofile import UserProfile


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


class ProductAdmin(ReadOnlyModelAdmin):
    """Products, maintained on Stripe.

    Users may not edit these products. They set up Prices and Products on the
    Stripe Dashboard, then call `python ./manage.py import-plans-from-stripe`.
    """

    ordering = ("stripe_product_name",)


class PriceAdmin(ReadOnlyModelAdmin):
    """Prices, maintained on Stripe.

    Users may not edit these prices. They set up Prices and Products on the
    Stripe Dashboard, then call `python ./manage.py import-plans-from-stripe`.
    """

    ordering = ("product__stripe_product_name", "stripe_amount")


admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Price, PriceAdmin)
admin.site.register(Product, ProductAdmin)
