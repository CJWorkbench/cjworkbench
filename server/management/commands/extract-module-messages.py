import logging
import os.path
import pathlib
import shutil
import tempfile
import time
from django.core.management.base import BaseCommand
from cjwstate.modules.module_loader import ModuleFiles, ModuleSpec
from cjwstate.modules.i18n.catalogs.update import extract_module_messages
import cjwstate.modules


logger = logging.getLogger(__name__)


def main(directory, force_update):
    cjwstate.modules.init_module_system()
    path = pathlib.Path(directory)

    if force_update:
        logger.info(f"Force extracting...")
    else:
        logger.info(f"Extracting...")

    extract_module_messages(path, force_update=force_update)


class Command(BaseCommand):
    help = "Find the internationalized texts of a module and export them to po files."

    def add_arguments(self, parser):
        parser.add_argument("directory")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Update the catalogs even if there are no new contents",
        )

    def handle(self, *args, **options):
        main(options["directory"], options["force"])
