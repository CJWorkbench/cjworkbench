import logging
import os
import pathlib
import time
from django.core.management.base import BaseCommand
from watchdog.events import RegexMatchingEventHandler
from watchdog.observers import Observer
from cjwstate.importmodule import import_module_from_directory
from cjwstate.modules.i18n.catalogs.update import extract_module_messages
import cjwstate.modules


logger = logging.getLogger(__name__)


def main(directory):
    cjwstate.modules.init_module_system()
    path = pathlib.Path(directory)

    def reload():
        if os.path.isdir(path / "locale"):
            try:
                logger.info(f"Extracting i18n messages...")
                extract_module_messages(path)
            except Exception:
                logger.exception("Error extracting module translations")
                return

        try:
            logger.info(f"Importing module...")
            import_module_from_directory(path)
        except Exception:
            logger.exception("Error loading module")

    class ReloadEventHandler(RegexMatchingEventHandler):
        def on_any_event(self, ev):
            reload()

    regexes = [".*\\.(py|json|yaml|html|po|pot)"]

    event_handler = ReloadEventHandler(regexes=regexes)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()

    reload()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


class Command(BaseCommand):
    help = "Watch a directory and auto-import its module."

    def add_arguments(self, parser):
        parser.add_argument("directory")

    def handle(self, *args, **options):
        main(options["directory"])
