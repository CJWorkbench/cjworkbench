from inspect import iscoroutinefunction
from asgiref.sync import async_to_sync


class MockParams:
    @staticmethod
    def factory(**kwargs):
        """Build a MockParams factory with default values.

        Usage:

            P = MockParams.factory(foo=3)
            params = P(bar=2)  # {'foo': 3, 'bar': 2}
        """
        return lambda **d: {**kwargs, **d}


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
