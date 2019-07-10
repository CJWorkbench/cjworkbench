from django import forms
from django.contrib.auth import get_user_model
from cjworkbench.models.userprofile import UserProfile


class WorkbenchSignupForm(forms.ModelForm):
    get_newsletter = forms.BooleanField(required=False, initial=True)
    field_order = [
        "email",
        "first_name",
        "last_name",
        "password1",
        "password2",
        "get_newsletter",
    ]

    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
        }

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()
        # User profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.get_newsletter = self.cleaned_data["get_newsletter"]
        profile.save()
