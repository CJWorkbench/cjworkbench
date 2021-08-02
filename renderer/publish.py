import datetime
import gzip
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import cjwparquet
import pyarrow as pa
from django.conf import settings
from django.utils.text import slugify

from cjwkernel.util import json_encode, tempfile_context
from cjwkernel.types import Column, ColumnType
from cjwstate import s3
from .execute.types import TabResult


DELAY_FROM_DATASET_EXPIRED_TO_DELETED = datetime.timedelta(days=1)


def _get_latest_revision(workflow_id: int) -> int:
    """Return the latest revision, or raise FileNotFoundError."""
    with s3.temporarily_download(
        s3.DatasetsBucket, f"wf-{workflow_id}/datapackage.json"
    ) as path, open(path, "rb") as f:
        return json.load(f)["_workbenchRevision"]


def _arrow_type_to_frictionless_field_type(arrow_type: pa.DataType) -> str:
    if pa.types.is_timestamp(arrow_type):
        return "datetime"
    elif pa.types.is_date32(arrow_type):
        return "date"
    elif pa.types.is_integer(arrow_type) or pa.types.is_floating(arrow_type):
        return "number"
    elif (
        pa.types.is_dictionary(arrow_type)
        and pa.types.is_unicode(arrow_type.value_type)
    ) or pa.types.is_unicode(arrow_type):
        return "string"
    else:
        raise ValueError("Unexpected arrow_type %r" % (arrow_type,))


def _build_frictionless_table_schema(schema: pa.Schema) -> Dict[str, Any]:
    return dict(
        fields=[
            dict(name=name, type=_arrow_type_to_frictionless_field_type(arrow_type))
            for name, arrow_type in zip(schema.names, schema.types)
        ]
    )


def _md5sum(path: Path) -> str:
    BLOCK_SIZE = 10 * 1024 * 1024  # arbitrary
    m = hashlib.md5()
    with open(path, "rb") as f:
        while (block := f.read(BLOCK_SIZE)) != b"":
            m.update(block)
    return m.hexdigest()


def _publish_tab_parquet_resource(
    *,
    url_prefix: str,
    s3_prefix: str,
    slug: str,
    title: str,
    parquet_path: Path,
    arrow_schema: pa.Schema,
):
    inner_path = f"/data/{slug}_parquet.parquet"
    s3.fput_file(s3.DatasetsBucket, s3_prefix + inner_path, parquet_path)
    md5sum = _md5sum(parquet_path)
    size = parquet_path.stat().st_size

    return dict(
        profile="data-resource",
        name=slug + "_parquet",
        path=url_prefix + inner_path,
        title=title,
        format="parquet",
        schema=_build_frictionless_table_schema(arrow_schema),
        hash=md5sum,
        bytes=size,
    )


def run_subprocess_and_pipe_stdout_to_file_object(cmd, *, stdout, **kwargs):
    """Like subprocess.run(cmd, stdout=stdout, **kwargs) ... with a file object.

    subprocess.run() will normally pass a file descriptor to the subprocess.
    We need special code to pass a file *object*: we need to read in a loop.
    """
    if "stdin" in kwargs or "stderr" in kwargs:
        # This would be too complicated.
        raise TypeError("Cannot stream from subprocess if stdin or stderr are provided")

    with subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0, **kwargs) as proc:
        shutil.copyfileobj(proc.stdout, stdout)
        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError(
                "%r returned non-zero returncode: %d" % (args, proc.returncode)
            )


def _publish_tab_csv_resource(
    *,
    url_prefix: str,
    s3_prefix: str,
    slug: str,
    title: str,
    arrow_schema: pa.Schema,
    parquet_path: Path,
):
    inner_path = f"/data/{slug}_csv.csv.gz"

    with tempfile_context(suffix=".csv.gz") as csv_path:
        with open(csv_path, "wb", buffering=0) as wf, gzip.GzipFile(
            filename=f"{slug}_csv.csv",
            mode="wb",
            fileobj=wf,
            compresslevel=3,
            mtime=0,
        ) as wzf:
            run_subprocess_and_pipe_stdout_to_file_object(
                ["/usr/bin/parquet-to-text-stream", parquet_path, "csv"],
                stdout=wzf,
            )

        s3.fput_file(s3.DatasetsBucket, s3_prefix + inner_path, csv_path)
        md5sum = _md5sum(csv_path)
        size = csv_path.stat().st_size
    return dict(
        profile="tabular-data-resource",
        name=slug + "_csv",
        path=url_prefix + inner_path,
        title=title,
        format="csv",
        compression="gz",
        schema=_build_frictionless_table_schema(arrow_schema),
        hash=md5sum,
        bytes=size,
    )


def _publish_tab_json_resource(
    *,
    url_prefix: str,
    s3_prefix: str,
    slug: str,
    title: str,
    arrow_schema: pa.Schema,
    parquet_path: Path,
):
    inner_path = f"/data/{slug}_json.json.gz"

    with tempfile_context(suffix=".json") as json_path:
        with json_path.open("wb") as wf, gzip.GzipFile(
            filename=f"{slug}_json.json",
            mode="wb",
            fileobj=wf,
            compresslevel=3,
            mtime=0,
        ) as wzf:
            run_subprocess_and_pipe_stdout_to_file_object(
                ["/usr/bin/parquet-to-text-stream", parquet_path, "json"],
                stdout=wzf,
            )

        s3.fput_file(s3.DatasetsBucket, s3_prefix + inner_path, json_path)
        md5sum = _md5sum(json_path)
        size = json_path.stat().st_size
    return dict(
        profile="data-resource",
        name=slug + "_json",
        path=url_prefix + inner_path,
        title=title,
        format="json",
        compression="gz",
        schema=_build_frictionless_table_schema(arrow_schema),
        hash=md5sum,
        bytes=size,
    )


def _publish_tab_resources(
    *, url_prefix: str, s3_prefix: str, tab_result: TabResult
) -> List[Dict[str, Any]]:
    slug = slugify(tab_result.tab_name)
    with tempfile_context(suffix=".parquet") as parquet_path:
        with pa.ipc.open_file(tab_result.path) as arrow_reader:
            arrow_table = arrow_reader.read_all()
            arrow_schema = arrow_table.schema

            cjwparquet.write(parquet_path, arrow_table)

        parquet_resource = _publish_tab_parquet_resource(
            url_prefix=url_prefix,
            s3_prefix=s3_prefix,
            slug=slug,
            title=tab_result.tab_name,
            arrow_schema=arrow_schema,
            parquet_path=parquet_path,
        )
        csv_resource = _publish_tab_csv_resource(
            url_prefix=url_prefix,
            s3_prefix=s3_prefix,
            slug=slug,
            title=tab_result.tab_name,
            arrow_schema=arrow_schema,
            parquet_path=parquet_path,
        )
        json_resource = _publish_tab_json_resource(
            url_prefix=url_prefix,
            s3_prefix=s3_prefix,
            slug=slug,
            title=tab_result.tab_name,
            arrow_schema=arrow_schema,
            parquet_path=parquet_path,
        )
    return [parquet_resource, csv_resource, json_resource]


def _publish_datapackage(
    *,
    url_prefix: str,
    s3_prefix: str,
    workflow_id: int,
    workflow_name: str,
    revision: int,
    resources: List[Dict[str, Any]],
) -> Dict[str, Any]:
    package_name = f"{workflow_id}-{slugify(workflow_name)}"
    datapackage = dict(
        profile="data-package",
        version=f"0.1.{revision}",
        path=url_prefix + "/datapackage.json",
        title=workflow_name,
        name=package_name,
        created=datetime.datetime.utcnow().isoformat() + "Z",
        resources=resources,
        _workbenchRevision=revision,
    )
    contents = json_encode(datapackage).encode("utf-8")
    s3.put_bytes(s3.DatasetsBucket, s3_prefix + "/datapackage.json", contents)
    return datapackage


async def publish_dataset(
    *,
    workflow_id: int,
    workflow_name: str,
    readme_md: str,
    tab_results: List[TabResult],
) -> Dict[str, Any]:
    """Write Frictionless datasets to S3: Parquet, CSV and JSON.

    The workflow must be locked: this function cannot be called twice on the
    same workflow at the same time.

    Return a Frictionless Data spec
    """
    try:
        last_revision = _get_latest_revision(workflow_id)
        revision = last_revision + 1
    except FileNotFoundError:
        last_revision = None
        revision = 1

    s3_prefix = f"wf-{workflow_id}/r{revision}"
    url_prefix = f"{settings.API_URL}/v1/datasets/{workflow_id}-{slugify(workflow_name)}/r{revision}"

    s3.remove_recursive(s3.DatasetsBucket, s3_prefix + "/")

    if readme_md:
        # Don't publish empty README.md: boto3 can't upload empty files to minio
        # https://github.com/minio/minio/issues/11245
        s3.put_bytes(
            s3.DatasetsBucket, s3_prefix + "/README.md", readme_md.encode("utf-8")
        )

    resources = []
    for tab_result in tab_results:
        resources.extend(
            _publish_tab_resources(
                url_prefix=url_prefix, s3_prefix=s3_prefix, tab_result=tab_result
            )
        )

    frictionless_datapackage_spec = _publish_datapackage(
        url_prefix=url_prefix,
        s3_prefix=s3_prefix,
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        revision=revision,
        resources=resources,
    )

    # Mark this revision the "current" one.
    s3.copy(
        s3.DatasetsBucket,
        f"wf-{workflow_id}/datapackage.json",
        f"{s3.DatasetsBucket}/{s3_prefix}/datapackage.json",
    )

    # Mark previous revision for deletion
    if last_revision:
        for key in s3.list_file_keys(
            s3.DatasetsBucket, f"wf-{workflow_id}/r{last_revision}/"
        ):
            expires = datetime.datetime.utcnow() + DELAY_FROM_DATASET_EXPIRED_TO_DELETED
            # [adamhooper, 2021-07-22] tested on S3: overwrite updates LastModified
            # [adamhooper, 2021-07-22] tested on GCS: overwrite updates LastModified
            # tested on minio: nope. https://github.com/minio/minio/issues/12777
            # So let's just overwrite some metadata, as a placeholder until
            # https://www.pivotaltracker.com/story/show/178977059
            s3.copy(
                s3.DatasetsBucket,
                key,
                f"{s3.DatasetsBucket}/{key}",
                MetadataDirective="REPLACE",
                Metadata={"cjw-expires": expires.isoformat() + "Z"},
            )

    return frictionless_datapackage_spec
