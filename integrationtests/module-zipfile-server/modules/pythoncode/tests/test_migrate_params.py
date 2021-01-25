from pythoncode import migrate_params


def test_v0():
    assert migrate_params({"run": "", "code": "def process(x):\n  return x"}) == {
        "code": "def process(x):\n  return x"
    }


def test_v1():
    assert migrate_params({"code": "def process(x):\n  return x"}) == {
        "code": "def process(x):\n  return x"
    }
