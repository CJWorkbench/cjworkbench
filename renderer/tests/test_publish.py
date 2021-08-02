import asyncio
import datetime
import gzip
import hashlib
import json
import time
from contextlib import ExitStack

import pyarrow as pa
import cjwparquet
from cjwmodule.arrow.testing import make_column, make_table
from django.test import override_settings

from cjwkernel.tests.util import arrow_table_context
from cjwkernel.util import tempdir_context
from cjwkernel.validate import read_columns
from cjwstate import s3
from cjwstate.tests.utils import DbTestCase
from renderer.execute.types import TabResult
from renderer.publish import publish_dataset


def md5digest(data: bytes) -> str:
    md5 = hashlib.md5()
    md5.update(data)
    return md5.hexdigest()


@override_settings(API_URL="https://api.test")
class PublishTests(DbTestCase):
    def setUp(self):
        super().setUp()
        self.exit_stack = ExitStack()
        self.basedir = self.exit_stack.enter_context(tempdir_context())

    def tearDown(self):
        self.exit_stack.close()
        super().tearDown()

    def _write_tab_result(self, tab_name: str, table: pa.Table) -> TabResult:
        path, _ = self.exit_stack.enter_context(
            arrow_table_context(table, dir=self.basedir)
        )
        return TabResult(tab_name, path, read_columns(table))

    def test_publish_parquet(self):
        tab1_result = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["a"]))
        )

        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab1_result],
            )
        )

        cjwparquet.write(
            self.basedir / "expected.parquet", make_table(make_column("A", ["a"]))
        )
        s3.download(
            s3.DatasetsBucket,
            "wf-123/r1/data/tab-1_parquet.parquet",
            self.basedir / "actual.parquet",
        )
        self.assertTrue(
            cjwparquet.are_files_equal(
                self.basedir / "actual.parquet", self.basedir / "expected.parquet"
            )
        )
        s3.download(
            s3.DatasetsBucket,
            "wf-123/r1/datapackage.json",
            self.basedir / "datapackage.json",
        )
        resource = next(
            resource
            for resource in json.loads(
                (self.basedir / "datapackage.json").read_bytes()
            )["resources"]
            if resource["name"] == "tab-1_parquet"
        )
        self.assertEqual(
            resource,
            dict(
                profile="data-resource",
                name="tab-1_parquet",
                path="https://api.test/v1/datasets/123-workflow-1/r1/data/tab-1_parquet.parquet",
                title="Tab 1",
                format="parquet",
                schema={"fields": [{"name": "A", "type": "string"}]},
                hash=md5digest((self.basedir / "actual.parquet").read_bytes()),
                bytes=(self.basedir / "actual.parquet").stat().st_size,
            ),
        )

    def test_publish_multiple_tabs(self):
        tab1_result = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["a"]))
        )
        tab2_result = self._write_tab_result(
            "Tab 2", make_table(make_column("B", ["b"]))
        )

        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab1_result, tab2_result],
            )
        )

        cjwparquet.write(
            self.basedir / "expected-1.parquet", make_table(make_column("A", ["a"]))
        )
        cjwparquet.write(
            self.basedir / "expected-2.parquet", make_table(make_column("B", ["b"]))
        )
        s3.download(
            s3.DatasetsBucket,
            "wf-123/r1/data/tab-1_parquet.parquet",
            self.basedir / "actual-1.parquet",
        )
        s3.download(
            s3.DatasetsBucket,
            "wf-123/r1/data/tab-2_parquet.parquet",
            self.basedir / "actual-2.parquet",
        )
        self.assertTrue(
            cjwparquet.are_files_equal(
                self.basedir / "actual-1.parquet", self.basedir / "expected-1.parquet"
            )
        )
        self.assertTrue(
            cjwparquet.are_files_equal(
                self.basedir / "actual-2.parquet", self.basedir / "expected-2.parquet"
            )
        )

    def test_overwrite_incomplete_new_revision(self):
        # Publish r1
        tab1_result = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["a"]))
        )
        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab1_result],
            )
        )
        # Now, r2 is a revision that "failed" to upload: some files are there,
        # but they aren't referenced
        s3.put_bytes(
            s3.DatasetsBucket, "wf-123/r2/data/tab-x_parquet.parquet", b"corrupt"
        )

        # Publish a new revision
        tab1_result2 = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["b"]))
        )
        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab1_result2],
            )
        )

        self.assertFalse(
            s3.exists(s3.DatasetsBucket, "wf-123/r2/data/tab-x_parquet.parquet")
        )
        self.assertTrue(
            s3.exists(s3.DatasetsBucket, "wf-123/r2/data/tab-1_parquet.parquet")
        )
        # And the old revision wasn't touched...
        self.assertTrue(
            s3.exists(s3.DatasetsBucket, "wf-123/r1/data/tab-1_parquet.parquet")
        )

    def test_publish_csv(self):
        tab1_result = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["a", None]), make_column("B", [2, 3]))
        )

        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab1_result],
            )
        )

        expected_data = b"A,B\r\na,2\r\n,3"
        s3.download(
            s3.DatasetsBucket,
            "wf-123/r1/data/tab-1_csv.csv.gz",
            self.basedir / "actual.csv.gz",
        )
        self.assertEqual(
            gzip.decompress((self.basedir / "actual.csv.gz").read_bytes()),
            expected_data,
        )
        s3.download(
            s3.DatasetsBucket,
            "wf-123/r1/datapackage.json",
            self.basedir / "datapackage.json",
        )
        resource = next(
            resource
            for resource in json.loads(
                (self.basedir / "datapackage.json").read_bytes()
            )["resources"]
            if resource["name"] == "tab-1_csv"
        )
        self.assertEqual(
            resource,
            dict(
                profile="tabular-data-resource",
                name="tab-1_csv",
                path="https://api.test/v1/datasets/123-workflow-1/r1/data/tab-1_csv.csv.gz",
                title="Tab 1",
                format="csv",
                compression="gz",
                schema={
                    "fields": [
                        {"name": "A", "type": "string"},
                        {"name": "B", "type": "number"},
                    ]
                },
                hash=md5digest((self.basedir / "actual.csv.gz").read_bytes()),
                bytes=(self.basedir / "actual.csv.gz").stat().st_size,
            ),
        )

    def test_publish_json(self):
        tab1_result = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["a", None]), make_column("B", [2, 3]))
        )

        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab1_result],
            )
        )

        expected_data = b'[{"A":"a","B":2},{"A":null,"B":3}]'
        s3.download(
            s3.DatasetsBucket,
            "wf-123/r1/data/tab-1_json.json.gz",
            self.basedir / "actual.json.gz",
        )
        self.assertEqual(
            gzip.decompress((self.basedir / "actual.json.gz").read_bytes()),
            expected_data,
        )
        s3.download(
            s3.DatasetsBucket,
            "wf-123/r1/datapackage.json",
            self.basedir / "datapackage.json",
        )
        resource = next(
            resource
            for resource in json.loads(
                (self.basedir / "datapackage.json").read_bytes()
            )["resources"]
            if resource["name"] == "tab-1_json"
        )
        self.assertEqual(
            resource,
            dict(
                profile="data-resource",
                name="tab-1_json",
                path="https://api.test/v1/datasets/123-workflow-1/r1/data/tab-1_json.json.gz",
                title="Tab 1",
                format="json",
                compression="gz",
                schema={
                    "fields": [
                        {"name": "A", "type": "string"},
                        {"name": "B", "type": "number"},
                    ]
                },
                hash=md5digest((self.basedir / "actual.json.gz").read_bytes()),
                bytes=(self.basedir / "actual.json.gz").stat().st_size,
            ),
        )

    def test_publish_new_revision_and_mark_old_revision_for_deletion(self):
        tab_result1 = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["a"]))
        )
        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab_result1],
            )
        )
        tab_result2 = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["b"]))
        )

        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab_result2],
            )
        )

        expire_before_or_at = (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        ).isoformat() + "Z"

        for key in [
            "wf-123/r1/datapackage.json",
            "wf-123/r1/data/tab-1_csv.csv.gz",
            "wf-123/r1/data/tab-1_json.json.gz",
            "wf-123/r1/data/tab-1_parquet.parquet",
        ]:
            # Assert the object has an "expired" tag and a creation date _after_
            # r2 was published. This is enough for us to create a lifecycle rule
            # that deletes 24hrs or more in the future.
            self.assertLessEqual(
                s3.layer.client.head_object(Bucket=s3.DatasetsBucket, Key=key)[
                    "Metadata"
                ]["cjw-expires"],
                expire_before_or_at,
                f"{key} expiry must come before {expire_before_or_at}",
            )

    def test_return_frictionless_datapackage_spec(self):
        tab_result = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["a"]))
        )
        ret = asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="",
                tab_results=[tab_result],
            )
        )
        self.assertEqual(
            ret["path"],
            "https://api.test/v1/datasets/123-workflow-1/r1/datapackage.json",
        )

    def test_publish_readme_md(self):
        tab_result = self._write_tab_result(
            "Tab 1", make_table(make_column("A", ["a"]))
        )
        asyncio.run(
            publish_dataset(
                workflow_id=123,
                workflow_name="Workflow 1",
                readme_md="# Heading\n\nbody",
                tab_results=[tab_result],
            )
        )
        s3.download(
            s3.DatasetsBucket, "wf-123/r1/README.md", self.basedir / "README.md"
        )
        self.assertEqual(
            (self.basedir / "README.md").read_bytes(), b"# Heading\n\nbody"
        )
