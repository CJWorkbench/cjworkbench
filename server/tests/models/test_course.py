import textwrap
import unittest
import yaml
from ..utils import MockPath, MockDir
from server.models.course import Course
from server.models.lesson import Lesson, LessonHeader, LessonFooter


class CourseTests(unittest.TestCase):
    def test_happy_path(self):
        dirpath = MockDir({
            'index.yaml': textwrap.dedent('''\
                title: Title
                introduction_html: |-
                    <p>Hi</p>
                    <p>Bye</p>
                lessons:
                    - lesson-1
                    - lesson-2
                ''').encode('utf-8'),
            'lesson-1.html': (
                b'<header><h1>L1</h1><p>HP1</p></header>'
                b'<footer><h2>F1</h2><p>foot</p></footer>'
            ),
            'lesson-2.html': (
                b'<header><h1>L2</h1><p>HP2</p></header>'
                b'<footer><h2>F2</h2><p>foot</p></footer>'
            ),
        })
        assert dirpath.name == 'root'  # we define this in 'utils'
        course = Course.load_from_path(dirpath / 'index.yaml')
        self.assertEqual(course, Course(
            slug='root',
            title='Title',
            introduction_html='<p>Hi</p>\n<p>Bye</p>',
            lessons=[
                Lesson('lesson-1',
                       header=LessonHeader('L1', '<p>HP1</p>'),
                       footer=LessonFooter('F1', '<p>foot</p>')),
                Lesson('lesson-2',
                       header=LessonHeader('L2', '<p>HP2</p>'),
                       footer=LessonFooter('F2', '<p>foot</p>')),
            ]
        ))

    def test_lesson_file_not_found(self):
        dirpath = MockDir({
            'index.yaml': textwrap.dedent('''\
                title: Title
                introduction_html: <p>hi</p>
                lessons:
                    - lesson-x
                ''').encode('utf-8'),
        })
        with self.assertRaisesRegex(FileNotFoundError, 'lesson-x.html'):
            Course.load_from_path(dirpath / 'index.yaml')

    def test_lesson_missing_title(self):
        dirpath = MockDir({
            'index.yaml': textwrap.dedent('''\
                introduction_html: <p>hi</p>
                lessons: []
                ''').encode('utf-8')
        })
        with self.assertRaisesRegex(KeyError, 'title'):
            Course.load_from_path(dirpath / 'index.yaml')

    def test_lesson_invalid_yaml(self):
        dirpath = MockDir({
            'index.yaml': b'{',
        })
        with self.assertRaises(yaml.YAMLError):
            Course.load_from_path(dirpath / 'index.yaml')

    def test_lesson_missing_index(self):
        dirpath = MockDir({})
        with self.assertRaisesRegex(FileNotFoundError, 'index.yaml'):
            Course.load_from_path(dirpath / 'index.yaml')
