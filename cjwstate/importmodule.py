import hashlib
import logging
import json
from pathlib import Path
import re
import shutil
import zipfile
import httpx
import pathspec
from cjwkernel.errors import ModuleError
from cjwkernel.util import tempdir_context
from cjwstate import minio
from cjwstate.models import ModuleVersion
from cjwstate import clientside
import cjwstate.modules
from cjwstate.modules.types import ModuleZipfile


logger = logging.getLogger(__name__)


class WorkbenchModuleImportError(Exception):
    """
    An Exception importing the module.

    All messages are in English. (TODO consider i18n for them.)
    """


GITHUB_URL_PATTERN = re.compile(
    "^https?://github.com/(?P<owner>[^/+])/(?P<repo>[^.]+)(?:.git)?$"
)
TEST_ZIP_URL_PATTERN = re.compile(
    "^http://module-zipfile-server/(?P<zipfile>[a-z][a-z0-9]*\.[a-f0-9]+\.zip)$"
)


def _resolve_github_ref(owner: str, repo: str, ref: str) -> str:
    """
    Given a GitHub owner/repo/ref, return the sha1 at that ref.

    Raise WorkbenchModuleImportError if the HTTP request fails or GitHub says
    there is no such ref. These errors are all in English, since we assume most
    module authors can read English and it takes effort to translate technical
    messages.
    """
    try:
        # raise HTTPError
        response = httpx.get(
            "https://api.github.com/repos/%s/%s/git/ref/heads/%s" % (owner, repo, ref),
            headers=[("Accept", "application/vnd.github.v3+json")],
        )
        # raise HTTPError
        response.raise_for_status()
    except httpx.HTTPError as err:
        raise WorkbenchModuleImportError(
            "HTTP error asking GitHub to resolve ref %(ref)s: %(message)s"
            % {"ref": ref, "message": str(err)}
        )

    data = json.loads(response.text)
    return data["object"]["sha"]


def _download_url(url: str, dest: Path) -> None:
    """
    Download archive from URL to file `dest`.

    Raise `WorkbenchModuleImportError` on HTTP error.
    """
    try:
        with dest.open("wb") as w:
            with httpx.stream("GET", url) as r:
                for chunk in r.iter_bytes():
                    w.write(chunk)
    except httpx.HTTPError as err:
        raise WorkbenchModuleImportError(
            "HTTP error downloading %(url)s: %(message)s"
            % dict(url=url, message=str(err))
            % {"url": url, "message": str(err)}
        )


def _download_github_module(owner: str, repo: str, sha1: str, dest: Path) -> None:
    """
    Download archive from GitHub to file `dest`.

    Raise `WorkbenchModuleImportError` on HTTP error.
    """
    _download_url("https://github.com/%s/%s/archive/%s.zip" % (owner, repo, sha1), dest)


def _validate_zipfile(module_zipfile: ModuleZipfile) -> None:
    """
    Ensure `path` points to a valid ModuleZipfile.

    Raise `WorkbenchModuleImportError` with an English-language description
    of the flaw otherwise. (This can help module authors fix their mistakes.)
    """
    try:
        module_zipfile.get_spec()  # raise KeyError, ValueError, BadZipFile
        # raise KeyError, UnicodeDecodeError, SyntaxError, BadZipFile
        compiled_module = module_zipfile.compile_code_without_executing()
        cjwstate.models.kernel.validate(compiled_module)  # raise ModuleError
        module_zipfile.get_optional_html()  # raise UnicodeError, BadZipFile
        module_zipfile.get_optional_js_module()  # raise UnicodeError, BadZipFile
    except zipfile.BadZipFile as err:
        raise WorkbenchModuleImportError("Bad zipfile: %s" % str(err))
    except ValueError as err:
        raise WorkbenchModuleImportError("Module .yaml is invalid: %s" % str(err))
    except KeyError as err:
        raise WorkbenchModuleImportError(
            "Zipfile is missing a required file: %s" % str(err)
        )
    except SyntaxError as err:
        raise WorkbenchModuleImportError(
            "Module Python code has a syntax error: %s" % str(err)
        )
    except UnicodeError as err:
        raise WorkbenchModuleImportError(
            "Module Python, HTML or JS code is invalid UTF-8: %s" % str(err)
        )
    except ModuleError as err:
        raise WorkbenchModuleImportError(
            "Module Python code failed to run: %s" % str(err)
        )


def import_zipfile(path: Path) -> clientside.Module:
    """
    Save a zipfile to database and minio and build a `clientside.Module`.

    Raise `WorkbenchModuleImportError` if `path` points to an invalid module.

    Otherwise, do not raise any errors one can sensibly recover from.
    """
    temp_zipfile = ModuleZipfile(path)
    _validate_zipfile(temp_zipfile)  # raise WorkbenchModuleImportError
    module_id = temp_zipfile.module_id
    version = temp_zipfile.version
    module_spec = temp_zipfile.get_spec()
    js_module = temp_zipfile.get_optional_js_module() or ""

    minio.fput_file(minio.ExternalModulesBucket, "%s/%s" % (module_id, path.name), path)
    ModuleVersion.objects.update_or_create(
        id_name=module_id,
        source_version_hash=version,
        spec=temp_zipfile.get_spec().data,
        js_module=js_module,
    )

    return clientside.Module(module_spec, js_module)


def import_module_from_github(
    owner: str, repo: str, ref: str = "master"
) -> clientside.Module:
    """
    Download module data from GitHub and store it in database+minio.

    Return a `clientside.Module` on success.

    Raise `WorkbenchModuleImportError` if import fails.
    """
    if owner.lower() != "cjworkbench":
        raise WorkbenchModuleImportError(
            "Refusing to import: according to the GitHub URL, "
            "this module is not owned by 'cjworkbench'"
        )
    sha1 = _resolve_github_ref(owner, repo, ref)  # raise WorkbenchModuleImportError

    with tempdir_context(prefix="importmodule") as td:
        name = "%s.%s.zip" % (repo, sha1)
        path = td / name
        _download_github_module(
            owner, repo, ref, path
        )  # raise WorkbenchModuleImportError
        return import_zipfile(path)  # raise WorkbenchModuleImportError


def import_module_from_test_zip_url(url: str, zipfile_name: str) -> clientside.Module:
    """
    Download module data from a zipfile at a trusted URL.

    Return a `clientside.Module` on success.

    Raise `WorkbenchModuleImportError` if import fails.
    """
    with tempdir_context(prefix="importmodule") as td:
        path = td / zipfile_name
        _download_url(url, path)  # raise WorkbenchModuleImportError
        return import_zipfile(path)  # raise WorkbenchModuleImportError


def import_module_from_url(url: str) -> clientside.Module:
    """
    Import zipfile from a URL.

    Return a `clientside.Module` on success.

    Raise `WorkbenchModuleImportError` if import fails, meaning:

    * The URL is not a URL we handle
    * There's an HTTP error
    * The ModuleZipfile is invalid
    """
    match = GITHUB_URL_PATTERN.match(url)
    if match:
        return import_module_from_github(match.group("owner"), match.group("repo"))

    if TEST_ZIP_URL_PATTERN.match(url):
        return import_module_from_test_zip_url(url)

    raise WorkbenchModuleImportError(
        "Please supply a GitHub URL with owner=CJWorkbench"
    )


def _hexsha1(path: Path) -> str:
    """Generate a hex sha1 digest from the file at `path`."""
    BLOCK_SIZE = 128 * 1024  # 128kb, chosen at random
    sha1 = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            block = f.read(BLOCK_SIZE)
            if not block:
                break
            sha1.update(block)
    return sha1.hexdigest()


def import_module_from_directory(dirpath: Path):
    """
    Create a zipfile using the files in a directory.

    Use `dirpath.name` as `module_id`. Use "dir-{hex-sha1sum of zipfile}" as
    `version`.

    Respect `.gitignore` to avoid importing too many files.

    Return a `clientside.Module` on success.

    Raise `WorkbenchModuleImportError` if import fails.
    """
    try:
        with (dirpath / ".gitignore").open("rt", encoding="utf-8") as f:
            gitignore = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern, f.readlines()
            )
    except FileNotFoundError:
        gitignore = pathspec.PathSpec([])

    module_id = dirpath.name
    with tempdir_context(prefix="importdir") as tempdir:
        unversioned_zip_path = tempdir / f"{module_id}.develop.zip"
        with zipfile.ZipFile(unversioned_zip_path, mode="w") as zf:
            for path in dirpath.glob("**/*"):
                if path.is_file():
                    relative_path = str(path.relative_to(path))
                    if not gitignore.match_file(relative_path):
                        zf.write(path, relative_path)

        version = "dir-" + _hexsha1(unversioned_zip_path)
        zip_path = f"{module_id}.{version}.zip"
        shutil.move(unversioned_zip_path, zip_path)
        return import_zipfile(zip_path)
