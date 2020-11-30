from unittest.mock import Mock, patch
from django.contrib.auth.models import User
from cjwstate import oauth
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile


class OauthTest(DbTestCaseWithModuleRegistry):
    @patch("cjwstate.oauth.OAuthService.lookup_or_none")
    def test_oauth1a_token_request_denied(self, lookup):
        lookup.return_value = Mock(oauth.OAuthService)
        lookup.return_value.generate_redirect_url_and_state.side_effect = (
            oauth.TokenRequestDenied("no!", {})
        )

        create_module_zipfile(
            "twitter",
            spec_kwargs={
                "parameters": [
                    {
                        "id_name": "twitter_credentials",
                        "type": "secret",
                        "secret_logic": {"provider": "oauth1a", "service": "twitter"},
                    }
                ],
            },
        )

        user = User.objects.create(username="a@example.org", email="a@example.org")
        self.client.force_login(user)
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            module_id_name="twitter", order=0, slug="step-1"
        )

        response = self.client.get(
            f"/oauth/create-secret/{workflow.id}/{step.id}/twitter_credentials/"
        )
        self.assertEqual(response.status_code, 403)
        self.assertRegex(
            response.content, b"The authorization server refused to let you log in"
        )
