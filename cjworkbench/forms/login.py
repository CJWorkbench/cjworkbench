from django import forms
import account.forms


class LoginEmailForm(account.forms.LoginEmailForm):
    def __init__(self, *args, **kwargs):
        super(LoginEmailForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].label_suffix = ""
