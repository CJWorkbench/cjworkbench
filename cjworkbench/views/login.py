import account.forms
import account.views

class LoginView(account.views.LoginView):
    form_class = account.forms.LoginEmailForm
