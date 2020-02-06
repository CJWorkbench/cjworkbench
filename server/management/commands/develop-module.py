import logging
import pathlib
import time
from django.core.management.base import BaseCommand
from watchdog.events import RegexMatchingEventHandler
from watchdog.observers import Observer
from cjwstate.importmodule import import_module_from_directory
import cjwstate.modules


logger = logging.getLogger(__name__)


def main(directory):
    cjwstate.modules.init_module_system()

    def reload():
        logger.info(f"Reloading...")

        try:
            import_module_from_directory(pathlib.Path(directory))
        except Exception:
            logger.exception("Error loading module")

    class ReloadEventHandler(RegexMatchingEventHandler):
        def on_any_event(self, ev):
            reload()

    regexes = [".*\\.(py|json|yaml|html)"]

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
