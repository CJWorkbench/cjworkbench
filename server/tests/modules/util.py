from unittest.mock import patch
from asgiref.sync import async_to_sync


class MockParams:
    """server.models.Params, based on a dict, no type-checking."""
    def __init__(self, **kwargs):
        self.d = kwargs

    def get_param(self, name, _type=None):
        return self.d[name.replace('-', '_')]

    def get_param_raw(self, name, _expected_type): return self.get_param(name)
    def get_param_string(self, name): return self.get_param(name)
    def get_param_integer(self, name): return self.get_param(name)
    def get_param_float(self, name): return self.get_param(name)
    def get_param_checkbox(self, name): return self.get_param(name)
    def get_param_radio_idx(self, name): return self.get_param(name)
    def get_param_radio_string(self, name): return self.get_param(name)
    def get_param_menu_idx(self, name): return self.get_param(name)
    def get_param_menu_string(self, name): return self.get_param(name)
    def get_param_secret_secret(self, name): return self.get_param(name)
    def get_param_column(self, name, _table): return self.get_param(name)
    def get_param_multicolumn(self, name, _table): return self.get_param(name)
    def get_param_json(self, name): return self.get_param(name)

    def to_painful_dict(self, table): return self.d

    @staticmethod
    def factory(**kwargs):
        """Build a MockParams factory with default values.

        Usage:

            P = MockParams.factory(foo=3)
            params = P(bar=2)  # {'foo': 3, 'bar': 2}
        """
        return lambda **d: MockParams(**{**kwargs, **d})


class MockWfModule:
    def __init__(self, params):
        self.params = params
        self.fetch_result = None

    def get_params(self):
        return self.params


def fetch_factory(func, params_klass):
    """
    Build a test-friendly fetch() function.

    Usage:

        P = MockParams.factory(x=1, y=2)
        fetch = fetch_factory(MyModule.fetch, P)

        # Build MockWfModule, run MyModule.fetch(wf_module), and commit the
        # result in as `wf_module.fetch_result` (may have status='error')
        wf_module = fetch(z=1)
    """
    async def _commit(wf_module, result, *args, **kwargs):
        wf_module.fetch_result = result

    def fetch(**kwargs):
        params = params_klass(**kwargs)
        wf_module = MockWfModule(params)

        with patch('server.modules.moduleimpl.ModuleImpl.commit_result',
                   _commit):
            async_to_sync(func)(wf_module)

        return wf_module

    return fetch
