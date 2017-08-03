from django import forms
import account.forms

class SignupForm(account.forms.SignupForm):
    get_newsletter = forms.BooleanField(required=False)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        del self.fields['username']
