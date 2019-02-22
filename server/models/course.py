from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import yaml
from .lesson import Lesson


def _load_lesson(path: Path) -> Lesson:
    slug = path.stem
    text = path.read_text()
    return Lesson.parse(slug, text)


@dataclass(frozen=True)
class Course:
    slug: str = ''
    title: str = ''
    introduction_html: str = ''
    lessons: List[Lesson] = field(default_factory=list)

    def find_lesson_by_slug(self, slug: str) -> Optional[Lesson]:
        """
        Return the matching Lesson, or `None` if it does not exist.
        """
        return next((l for l in self.lessons if l.slug == slug), None)

    @classmethod
    def load_from_path(cls, path: Path) -> Course:
        """
        Read a Course from the filesystem.

        `path` is a `index.yaml` file in a directory full of Lesson `.html`
        files. `index.yaml` looks like:

        title: [title]
        introduction_html: |-
            <p>Hi there</p>
            ...
        lessons:
            - lesson-1-slug
            - lesson-2-slug
            - ...

        May raise:

            * `FileNotFoundError` if `path` is missing.
            * `yaml.YAMLError` if index.yaml has the wrong syntax.
            * `KeyError` if `title`, `introduction_html` or `lessons` is
              missing.
            * `ValueError` or `TypeError` if they're the wrong type.
            * `LessonParseError` if any lesson is invalid.
            * `FileNotFoundError` if a referenced lesson does not exist.
        """
        dirpath = path.parent
        slug = dirpath.name
        data = yaml.safe_load(path.read_text())  # raises YAMLError
        title = str(data['title'])  # raises KeyError
        introduction_html = str(data['introduction_html'])  # raises KeyError
        lesson_slugs = list(data['lessons'])  # raises KeyError
        # raises FileNotFoundError, LessonParseError
        lessons = [_load_lesson(dirpath / (str(slug) + '.html'))
                   for slug in lesson_slugs]
        return cls(slug, title, introduction_html, lessons)


CourseLookup = dict(
    (course.slug, course)
    for course in [
        Course.load_from_path(path)
        for path in (
            (Path(__file__).parent.parent).glob('courses/**/index.yaml')
        )
    ]
)
