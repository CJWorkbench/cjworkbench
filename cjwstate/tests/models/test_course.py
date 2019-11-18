import textwrap
import unittest
import yaml
from cjwkernel.tests.util import MockDir, MockPath
from server.models.course import Course
from server.models.lesson import Lesson, LessonHeader, LessonFooter


class CourseTests(unittest.TestCase):
    def test_happy_path(self):
        dirpath = MockDir(
            {
                "en/a-course/index.yaml": textwrap.dedent(
                    """\
                title: Title
                introduction_html: |-
                    <p>Hi</p>
                    <p>Bye</p>
                lessons:
                    - lesson-1
                    - lesson-2
                """
                ).encode("utf-8"),
                "en/a-course/lesson-1.html": (
                    b"<header><h1>L1</h1><p>HP1</p></header>"
                    b"<footer><h2>F1</h2><p>foot</p></footer>"
                ),
                "en/a-course/lesson-2.html": (
                    b"<header><h1>L2</h1><p>HP2</p></header>"
                    b"<footer><h2>F2</h2><p>foot</p></footer>"
                ),
            }
        )
        course = Course.load_from_path(dirpath / "en" / "a-course" / "index.yaml")
        self.assertEqual(
            course,
            Course(
                slug="a-course",
                title="Title",
                locale_id="en",
                introduction_html="<p>Hi</p>\n<p>Bye</p>",
                lessons={
                    "lesson-1": Lesson(
                        course,
                        "lesson-1",
                        "en",
                        header=LessonHeader("L1", "<p>HP1</p>"),
                        footer=LessonFooter("F1", "<p>foot</p>"),
                    ),
                    "lesson-2": Lesson(
                        course,
                        "lesson-2",
                        "en",
                        header=LessonHeader("L2", "<p>HP2</p>"),
                        footer=LessonFooter("F2", "<p>foot</p>"),
                    ),
                },
            ),
        )

    def test_lesson_file_not_found(self):
        dirpath = MockDir(
            {
                "index.yaml": textwrap.dedent(
                    """\
                title: Title
                introduction_html: <p>hi</p>
                lessons:
                    - lesson-x
                """
                ).encode("utf-8")
            }
        )
        with self.assertRaisesRegex(FileNotFoundError, "lesson-x.html"):
            Course.load_from_path(dirpath / "index.yaml")

    def test_lesson_missing_title(self):
        dirpath = MockDir(
            {
                "index.yaml": textwrap.dedent(
                    """\
                introduction_html: <p>hi</p>
                lessons: []
                """
                ).encode("utf-8")
            }
        )
        with self.assertRaisesRegex(KeyError, "title"):
            Course.load_from_path(dirpath / "index.yaml")

    def test_lesson_invalid_yaml(self):
        dirpath = MockDir({"index.yaml": b"{"})
        with self.assertRaises(yaml.YAMLError):
            Course.load_from_path(dirpath / "index.yaml")

    def test_lesson_missing_index(self):
        dirpath = MockDir({})
        with self.assertRaisesRegex(FileNotFoundError, "index.yaml"):
            Course.load_from_path(dirpath / "index.yaml")
