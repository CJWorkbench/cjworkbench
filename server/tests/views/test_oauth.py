from unittest.mock import Mock, patch
from django.contrib.auth.models import User
from server import oauth
from server.models import Workflow, ModuleVersion
from server.tests.utils import DbTestCase


class OauthTest(DbTestCase):
    @patch('server.oauth.OAuthService.lookup_or_none')
    def test_oauth1a_token_request_denied(self, lookup):
        lookup.return_value = Mock(oauth.OAuthService)
        lookup.return_value.generate_redirect_url_and_state.side_effect = \
            oauth.TokenRequestDenied('no!', {})

        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'ext',
            'name': '',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'auth', 'type': 'secret', 'name': 'Secret'}
            ]
        })

        user = User.objects.create(username='a@example.org',
                                   email='a@example.org')
        self.client.force_login(user)
        workflow = Workflow.objects.create(owner=user)
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(module_id_name='ext', order=0)

        response = self.client.get(
            f'/oauth/create-secret/{workflow.id}/{wf_module.id}/auth/'
        )
        self.assertEqual(response.status_code, 403)
        self.assertRegex(
            response.content,
            b'The authorization server refused to let you log in'
        )
