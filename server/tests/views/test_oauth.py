from unittest.mock import Mock, patch
from django.contrib.auth.models import User
from cjwstate import oauth
from cjwstate.models import Workflow, ModuleVersion
from cjwstate.tests.utils import DbTestCase


class OauthTest(DbTestCase):
    @patch("cjwstate.oauth.OAuthService.lookup_or_none")
    def test_oauth1a_token_request_denied(self, lookup):
        lookup.return_value = Mock(oauth.OAuthService)
        lookup.return_value.generate_redirect_url_and_state.side_effect = oauth.TokenRequestDenied(
            "no!", {}
        )

        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "twitter",
                "name": "",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "twitter_credentials",
                        "type": "secret",
                        "secret_logic": {"provider": "oauth1a", "service": "twitter"},
                    }
                ],
            }
        )

        user = User.objects.create(username="a@example.org", email="a@example.org")
        self.client.force_login(user)
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name="twitter", order=0, slug="step-1"
        )

        response = self.client.get(
            f"/oauth/create-secret/{workflow.id}/{wf_module.id}/twitter_credentials/"
        )
        self.assertEqual(response.status_code, 403)
        self.assertRegex(
            response.content, b"The authorization server refused to let you log in"
        )
