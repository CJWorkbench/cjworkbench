import hashlib
import io
import json
import zipfile
from typing import Any, Dict, Optional
from unittest.mock import Mock

from django.contrib.auth.models import User

import cjwstate.modules
from cjworkbench.tests.utils import DbTestCase as BaseDbTestCase
from cjwstate import s3
from cjwstate.models.module_version import ModuleVersion
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.modules.types import ModuleZipfile


class DbTestCase(BaseDbTestCase):
    def setUp(self):
        super().setUp()
        clear_s3()


# Derive from this to perform all tests logged in
class LoggedInTestCase(DbTestCase):
    def setUp(self):
        super().setUp()

        self.user = create_test_user()
        self.client.force_login(self.user)


def create_test_user(
    username="username", email="user@example.org", password="password"
):
    return User.objects.create(username=username, email=email, password=password)


class DbTestCaseWithModuleRegistry(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cjwstate.modules.init_module_system()  # create module tempdir


class DbTestCaseWithModuleRegistryAndMockKernel(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cjwstate.modules.init_module_system()  # create module tempdir

    def setUp(self):
        super().setUp()

        self._old_kernel = cjwstate.modules.kernel
        self.kernel = cjwstate.modules.kernel = Mock()
        self.kernel.validate.return_value = None  # assume all modules are valid
        # default migrate_params() returns {}. If we wrote
        # `self.kernel.migrate_params.side_effect = lambda m, p: p`, then
        # callers couldn't use `self.kernel.migrate_params.return_value = ...`
        self.kernel.migrate_params.return_value = {}
        # No default implementation of self.kernel.fetch
        # No default implementation of self.kernel.render

    def tearDown(self):
        cjwstate.modules.kernel = self._old_kernel

        super().tearDown()


def create_module_zipfile(
    module_id: str = "testmodule",
    *,
    version: Optional[str] = None,
    spec_kwargs: Dict[str, Any] = {},
    python_code: str = "",
    html: Optional[str] = None,
    js_module: str = "",
    extra_file_contents: Dict[str, bytes] = {},
) -> ModuleZipfile:
    """
    Create a ModuleZipfile, stored in the database and s3.

    If `version` is not supplied, generate one using the sha1 of the zipfile.
    This is usually what you want: s3 reads on overwrites are _eventually_
    consistent, so if you 1. write a file; 2. overwrite it; and 3. read it, the
    read might result in the file from step 1 or the file from step 2. A sha1
    version means overwrites will never modify data, solving the problem.
    """
    spec = {
        "id_name": module_id,
        "name": "Test Module",
        "category": "Clean",
        "parameters": [],
        **spec_kwargs,
    }

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w") as zf:
        zf.writestr(module_id + ".yaml", json.dumps(spec))
        zf.writestr(module_id + ".py", python_code.encode("utf-8"))
        if html is not None:
            zf.writestr(module_id + ".html", html.encode("utf-8"))
        if js_module:
            zf.writestr(module_id + ".js", js_module.encode("utf-8"))
        for path, content in extra_file_contents.items():
            zf.writestr(path, content)
    data = bytes(bio.getbuffer())
    if version is None:
        sha1 = hashlib.sha1()
        sha1.update(data)
        version = sha1.hexdigest()

    s3.put_bytes(
        s3.ExternalModulesBucket,
        "%s/%s.%s.zip" % (module_id, module_id, version),
        data,
    )
    ModuleVersion.objects.create(
        id_name=module_id, source_version_hash=version, spec=spec, js_module=js_module
    )
    return MODULE_REGISTRY.latest(module_id)


def clear_s3():
    buckets = (
        s3.UserFilesBucket,
        s3.StoredObjectsBucket,
        s3.ExternalModulesBucket,
        s3.CachedRenderResultsBucket,
        s3.TusUploadBucket,
    )

    if not hasattr(clear_s3, "_initialized"):
        # Ensure buckets exist -- only on first call
        for bucket in buckets:
            s3.ensure_bucket_exists(bucket)
        clear_s3._initialized = True

    for bucket in buckets:
        s3.remove_recursive(bucket, "/", force=True)


def get_s3_object_with_data(bucket: str, key: str, **kwargs) -> Dict[str, Any]:
    """Like client.get_object(), but response['Body'] is bytes."""
    response = s3.client.get_object(Bucket=bucket, Key=key, **kwargs)
    body = response["Body"]
    try:
        data = body.read()
    finally:
        body.close()
    return {**response, "Body": data}
