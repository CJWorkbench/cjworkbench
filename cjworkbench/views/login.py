import account.forms
import account.views
import cjworkbench.forms.login


class LoginView(account.views.LoginView):
    form_class = cjworkbench.forms.login.LoginEmailForm
