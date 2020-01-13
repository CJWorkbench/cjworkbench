from allauth.account import views
from cjworkbench.i18n import set_language_cookie


class LoginView(views.LoginView):
    def dispatch(self, request, *args, **kwargs):
        response = super(LoginView, self).dispatch(request, *args, **kwargs)
        if request.user.is_authenticated:
            set_language_cookie(response, request.user.user_profile.locale_id)
        return response
