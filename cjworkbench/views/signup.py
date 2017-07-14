import account.views
import cjworkbench.forms.signup

class SignupView(account.views.SignupView):
    form_class = cjworkbench.forms.signup.SignupForm
    identifier_field = 'email'

    def generate_username(self, form):
        username = form.cleaned_data['email']
        return username
