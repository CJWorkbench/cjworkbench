from inspect import iscoroutinefunction
from asgiref.sync import async_to_sync


class MockParams:
    """server.models.Params, based on a dict, no type-checking."""
    def __init__(self, **kwargs):
        self.d = kwargs

    def get_param(self, name, _type=None):
        return self.d[name.replace('-', '_')]

    def get_param_string(self, name): return self.get_param(name)

    def get_param_integer(self, name): return self.get_param(name)

    def get_param_float(self, name): return self.get_param(name)

    def get_param_checkbox(self, name): return self.get_param(name)

    def get_param_radio_idx(self, name): return self.get_param(name)

    def get_param_menu_idx(self, name): return self.get_param(name)

    def get_param_secret_secret(self, name): return self.get_param(name)

    def get_param_column(self, name, _table): return self.get_param(name)

    def get_param_multicolumn(self, name, _table, ignore_type=False):
        return self.get_param(name)

    def get_param_json(self, name): return self.get_param(name)

    def to_painful_dict(self, table):
        if table is None:
            raise ValueError('You must pass a DataFrame')

        return self.d

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

    def get_params(self):
        return self.params


def fetch_factory(func, params_klass):
    """
    Build a test-friendly fetch() function.

    Usage:

        P = MockParams.factory(x=1, y=2)
        fetch = fetch_factory(MyModule.fetch, P)

        # Build MockWfModule, run MyModule.fetch(wf_module)
        fetch_result = fetch(z=1)
    """
    def fetch(**kwargs):
        params = params_klass(**kwargs)
        wf_module = MockWfModule(params)
        if iscoroutinefunction(func):
            return async_to_sync(func)(wf_module)
        else:
            return func(wf_module)

    return fetch
