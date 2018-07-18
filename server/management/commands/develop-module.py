import os.path
import shutil
import tempfile
import time
from django.core.management.base import BaseCommand
from watchdog.events import RegexMatchingEventHandler
from watchdog.observers import Observer
from server.importmodulefromgithub import import_module_from_directory


def main(directory, pretend_git_url):
    basename = os.path.basename(directory)

    def reload():
        print(f'Reloading {basename}')
        # import_module_from_directory is unintuitive: it _destroys_ the input
        # directory.
        tmpdir = tempfile.mkdtemp()
        shutil.rmtree(tmpdir)
        shutil.copytree(directory, tmpdir)
        import_module_from_directory(pretend_git_url, basename, 'develop',
                                     tmpdir, force_reload=True)
        print('Reloaded')

    class ReloadEventHandler(RegexMatchingEventHandler):
        def on_any_event(self, ev):
            reload()

    regexes = ['.*\.(py|json|html)']

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
