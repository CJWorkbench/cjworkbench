import json
import logging
import os
from pathlib import Path
import shutil
import tempfile
import git
from git.exc import GitCommandError
import yaml
from server import minio
from server.models import ModuleVersion
from server.models.module_loader import ModuleFiles, ModuleSpec, \
        validate_python_functions


logger = logging.getLogger(__name__)



# Load a module after cloning from github
# This is the guts of our module import, also a good place to hook into for
# tests (bypassing github access). Returns a dictionary of info to display to
# user (category, repo name, author, id_name)
def import_module_from_directory(version: str, importdir: Path, force_reload=False):
    module_files = ModuleFiles.load_from_dirpath(importdir)  # raise ValueError
    spec = ModuleSpec.load_from_path(module_files.spec)  # raise ValueError
    validate_python_functions(module_files.code)  # raise ValueError

    if not force_reload:
        # Don't allow importing the same version twice
        try:
            ModuleVersion.objects.get(id_name=spec.id_name,
                                      source_version_hash=version)
            raise ValueError(
                f'Version {version} of module {spec.id_name}'
                ' has already been imported'
            )
        except ModuleVersion.DoesNotExist:
            # this is what we want
            pass

    if module_files.javascript:
        js_module = module_files.javascript.read_text(encoding='utf-8')
    else:
        js_module = ''

    # Copy whole directory to S3
    prefix = '%s/%s/' % (spec.id_name, version)

    try:
        # If files already exist, delete them so we can overwrite them.
        #
        # This can race: a fetcher/renderer may be loading the code to execute
        # it. But races are unlikely to affect anybody because:
        #
        # * If force_reload=True we're in dev or test, where we control
        #   everything.
        # * Otherwise, we've already checked there's no ModuleVersion, so
        #   probably nothing is trying and load what we're deleting here.
        minio.remove_recursive(minio.ExternalModulesBucket, prefix)
    except FileNotFoundError:
        pass  # common case: we aren't overwriting code

    minio.fput_directory_contents(minio.ExternalModulesBucket, prefix,
                                  Path(importdir))

    # If that succeeds, initialise module in our database
    module_version = ModuleVersion.create_or_replace_from_spec(
        spec,
        source_version_hash=version,
        js_module=js_module
    )

    logger.info('Imported module %s' % spec.id_name)

    return module_version


# Top level import, clones from github
# If force_relaod, reloads the module even if the version hasn't changed
# (normally, this is an error). On success, returnd a dict with (category,
# repo name, author, id_name) to tell user what happened
def import_module_from_github(url, force_reload=False):
    with tempfile.TemporaryDirectory(prefix='importmodulefromgithub') as td:
        # Clone into a _subdirectory_ of `td`. That way if the subdir is
        # deleted (as `git clone` is wont to do),
        # `tempfile.TemporaryDirectory()`'s `finally` block will still be able
        # to delete `td`.
        importdir = os.path.join(td, 'repo')
        os.mkdir(importdir)

        clone_kwargs = {}
        if url.startswith('https://github.com/'):
            # depth=1: do not clone entire repo -- just the latest commit. Not
            # every HTTP server supports `depth`. (Indeed, our integration-test
            # HTTP server doesn't.) But we know GitHub does.
            clone_kwargs['depth'] = 1

        try:
            repo = git.Repo.clone_from(url, importdir, **clone_kwargs)
        except GitCommandError as err:
            raise RuntimeError(f'Unable to clone {url}: {str(err)}')

        version = repo.head.commit.hexsha[:7]

        # Nix ".git" subdir: not a Git repo any more, just a dir
        shutil.rmtree(os.path.join(importdir, '.git'))

        return import_module_from_directory(version, Path(importdir), force_reload)
