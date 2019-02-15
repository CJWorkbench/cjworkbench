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

    @classmethod
    def load_from_path(cls, path: Path) -> Course:
        """
        Read a Course from the filesystem.

        `path` is a directory. It must contain a `index.yaml` that looks like:

        title: [title]
        introduction_html: |-
            <p>Hi there</p>
            ...
        lessons:
            - lesson-1-slug
            - lesson-2-slug
            - ...

        May raise:

            * `FileNotFoundError` if `path` or `path/'index.yaml'` is missing.
            * `yaml.YAMLError` if index.yaml has the wrong syntax.
            * `KeyError` if `title`, `introduction_html` or `lessons` is
              missing.
            * `ValueError` or `TypeError` if they're the wrong type.
            * `LessonParseError` if any lesson is invalid.
            * `FileNotFoundError` if a referenced lesson does not exist.
        """
        slug = path.name
        # raises YAMLError
        data = yaml.safe_load((path / 'index.yaml').read_text())
        title = str(data['title'])  # raises KeyError
        introduction_html = str(data['introduction_html'])
        lesson_slugs = list(data['lessons'])
        lessons = [_load_lesson(path / (str(slug) + '.html'))
                   for slug in lesson_slugs]
        return cls(slug, title, introduction_html, lessons)
