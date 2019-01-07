from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from server.models import Workflow
from server.handlers.types import HandlerRequest
from server.tests.utils import DbTestCase


class HandlerTestCase(DbTestCase):
    def build_request(self, **kwargs):
        request_kwargs = {
            'request_id': kwargs.get('request_id', 1),
            'scope': kwargs.get('scope', {
                'user': kwargs.get('user', AnonymousUser()),
                'session': kwargs.get('session', Session()),
                'headers': kwargs.get('headers', ()),
            }),
            'workflow': kwargs.get('workflow', Workflow()),
            'path': kwargs.get('path', 'test.path'),
            'arguments': kwargs.get('arguments', {}),
        }
        for key in (
            list(request_kwargs['scope'].keys())
            + list(request_kwargs.keys())
        ):
            try:
                del kwargs[key]
            except KeyError:
                pass

        # Turn other params, like `wf_module_id=123`, into
        # `arguments={'wf_module_id':123}`
        request_kwargs['arguments'].update(kwargs)

        return HandlerRequest(**request_kwargs)

    def run_handler(self, handler, **kwargs):
        request = self.build_request(**kwargs)
        return self.run_with_async_db(handler(request))

    def assertResponse(self, actual, data=None, error=''):
        self.assertEqual({'data': actual.data, 'error': actual.error},
                         {'data': data, 'error': error})