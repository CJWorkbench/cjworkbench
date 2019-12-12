import logging
import os.path
import pathlib
import shutil
import tempfile
import time
from django.core.management.base import BaseCommand
from cjwstate.modules.module_loader import ModuleFiles, ModuleSpec
from cjwstate.modules.message_catalogs import update_module_catalogs
import cjwstate.modules


logger = logging.getLogger(__name__)


def main(directory):
    cjwstate.modules.init_module_system()

    logger.info(f"Extracting...")

    with tempfile.TemporaryDirectory() as tmpdir:
        importdir = os.path.join(tmpdir, "importme")
        shutil.copytree(directory, importdir)
        shutil.rmtree(os.path.join(importdir, ".git"), ignore_errors=True)
        shutil.rmtree(os.path.join(importdir, ".eggs"), ignore_errors=True)
        shutil.rmtree(os.path.join(importdir, "node_modules"), ignore_errors=True)

        module_files = ModuleFiles.load_from_dirpath(
            pathlib.Path(importdir)
        )  # raise ValueError
        spec = ModuleSpec.load_from_path(module_files.spec)  # raise ValueError

    update_module_catalogs(spec)


class Command(BaseCommand):
    help = "Find the internationalized texts of a module and export them to po files."

    def add_arguments(self, parser):
        parser.add_argument("directory")

    def handle(self, *args, **options):
        main(options["directory"])
