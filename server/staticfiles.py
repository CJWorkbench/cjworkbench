from pathlib import Path
from django.contrib.staticfiles.finders import BaseFinder
from django.contrib.staticfiles.utils import matches_patterns
from django.core.files.storage import FileSystemStorage


class LessonSupportDataFinder(BaseFinder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = Path(__file__).parent
        self.storage = FileSystemStorage(location=str(self.root.resolve()))

    # override
    def find(self, path: str, all=False):
        full_path = self.root / path
        if full_path.exists():
            if all:
                return [str(full_path)]
            else:
                return str(full_path)
        return []  # what a bizarre API we're fulfilling

    # override
    def list(self, ignore_patterns):
        for path in self.root.glob("lessons/*/*/*.*"):
            if not matches_patterns(path.name, ignore_patterns):
                yield str(path.relative_to(self.root)), self.storage
        for path in self.root.glob("courses/*/*/*/*.*"):
            if not matches_patterns(path.name, ignore_patterns):
                yield str(path.relative_to(self.root)), self.storage
