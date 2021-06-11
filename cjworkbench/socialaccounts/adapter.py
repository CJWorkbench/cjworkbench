from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        raise RuntimeError(
            "Workbench's save-user logic is in WorkbenchSocialaccountSignupForm"
        )
