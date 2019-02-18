import logging
import os.path
import pathlib
import shutil
import tempfile
import time
from django.core.management.base import BaseCommand
from watchdog.events import RegexMatchingEventHandler
from watchdog.observers import Observer
from server.importmodulefromgithub import import_module_from_directory


logger = logging.getLogger(__name__)


def main(directory, pretend_git_url):
    def reload():
        logger.info(f'Reloading...')

        with tempfile.TemporaryDirectory() as tmpdir:
            importdir = os.path.join(tmpdir, 'importme')
            shutil.copytree(directory, importdir)
            shutil.rmtree(os.path.join(importdir, '.git'), ignore_errors=True)

            try:
                import_module_from_directory('develop',
                                             pathlib.Path(importdir),
                                             force_reload=True)
            except Exception:
                logger.exception('Error loading module')

    class ReloadEventHandler(RegexMatchingEventHandler):
        def on_any_event(self, ev):
            reload()

    regexes = ['.*\\.(py|json|html)']

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
    help = 'Watch a directory and auto-import its module.'

    def add_arguments(self, parser):
        parser.add_argument('directory')
        parser.add_argument('pretend_git_url')

    def handle(self, *args, **options):
        main(options['directory'], options['pretend_git_url'])
