from django.contrib import admin
from cjworkbench.models.userprofile import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    ordering = ("user__email",)
    readonly_fields = ("user",)
    search_fields = ("user__email", "user__username")


admin.site.register(UserProfile, UserProfileAdmin)
