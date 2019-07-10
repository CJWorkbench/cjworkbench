import account.views
import cjworkbench.forms.signup
import cjworkbench.models.userprofile


class SignupView(account.views.SignupView):
    form_class = cjworkbench.forms.signup.SignupForm
    identifier_field = "email"

    def generate_username(self, form):
        username = form.cleaned_data["email"]
        return username

    def create_profile(self, form):
        profile = self.created_user.user_profile
        profile.get_newsletter = form.cleaned_data["get_newsletter"]
        profile.save()

    def after_signup(self, form):
        self.created_user.first_name = form.cleaned_data["first_name"]
        self.created_user.last_name = form.cleaned_data["last_name"]
        self.created_user.save()
        self.create_profile(form)
        super(SignupView, self).after_signup(form)
