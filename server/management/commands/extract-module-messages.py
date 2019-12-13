import logging
import os.path
import pathlib
import shutil
import tempfile
import time
from django.core.management.base import BaseCommand
from cjwstate.modules.module_loader import ModuleFiles, ModuleSpec
from cjwstate.modules.i18n import update_module_catalogs
import cjwstate.modules


logger = logging.getLogger(__name__)


def main(directory):
    cjwstate.modules.init_module_system()
    path = pathlib.Path(directory)

    logger.info(f"Extracting...")

    update_module_catalogs(path)


class Command(BaseCommand):
    help = "Find the internationalized texts of a module and export them to po files."

    def add_arguments(self, parser):
        parser.add_argument("directory")

    def handle(self, *args, **options):
        main(options["directory"])
