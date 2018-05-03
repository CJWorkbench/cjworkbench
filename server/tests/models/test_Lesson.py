import os.path
from django.test import SimpleTestCase
from server.models.Lesson import Lesson, LessonHeader, LessonSection, LessonSectionStep, LessonParseError, LessonManager

class LessonTests(SimpleTestCase):
    def test_parse_header_in_html_body(self):
        out = Lesson.parse('a-slug', '<html><body><header><h1>Lesson</h1><p>p1</p><p>p2</p></header></body></html>')
        self.assertEquals(out, Lesson('a-slug', LessonHeader('Lesson', '<p>p1</p><p>p2</p>'), []))

    def test_parse_step(self):
        out = Lesson.parse('a-slug', '<header><h1>Lesson</h1><p>Contents</p></header><section><h2>Foo</h2><p>bar</p><ol class="steps"><li>1</li></ol></section>')
        self.assertEquals(out,
            Lesson(
                'a-slug',
                LessonHeader('Lesson', '<p>Contents</p>'),
                [ LessonSection('Foo', '<p>bar</p>', [ LessonSectionStep('1') ]) ]
            )
        )

    def test_parse_no_header(self):
        with self.assertRaisesMessage(LessonParseError, 'Lesson HTML needs a top-level <header>'):
            Lesson.parse('a-slug', '<h1>Foo</h1><p>body</p>')

    def test_parse_no_header_title(self):
        with self.assertRaisesMessage(LessonParseError, 'Lesson <header> needs a non-empty <h1> title'):
            Lesson.parse('a-slug', '<header><p>Contents</p></header>')

    def test_parse_no_section_title(self):
        with self.assertRaisesMessage(LessonParseError, 'Lesson <section> needs a non-empty <h2> title'):
            Lesson.parse('a-slug', '<header><h1>x</h1><p>y</p></header><section><ol class="steps"><li>foo</li></ol></section>')

    def test_parse_no_section_steps(self):
        out = Lesson.parse('a-slug', '<header><h1>x</h1><p>y</p></header><section><h2>title</h2><ol class="not-steps"><li>foo</li></ol></section>')
        self.assertEquals(out,
            Lesson(
                'a-slug',
                LessonHeader('x', '<p>y</p>'),
                [ LessonSection('title', '<ol class="not-steps"><li>foo</li></ol>', []) ]
            )
        )

class LessonManagerTests(SimpleTestCase):
    def build_manager(self, path=None):
        if path is None:
            path = os.path.join(os.path.dirname(__file__), 'lessons')

        return LessonManager(path)

    def test_get(self):
        out = self.build_manager().get('slug-1')
        self.assertEquals(out,
            Lesson(
                'slug-1',
                LessonHeader('Lesson', '<p>Contents</p>'),
                [
                    LessonSection('Foo', '<p>bar</p>', [
                        LessonSectionStep('Step One'),
                        LessonSectionStep('Step Two'),
                    ])
                ]
            )
        )

    def test_get_parse_error(self):
        manager = self.build_manager(path=os.path.join(os.path.dirname(__file__), 'broken-lesson'))
        with self.assertRaisesMessage(LessonParseError, 'Lesson HTML needs a top-level <header>'):
            manager.get('slug-1')

    def test_get_does_not_exist(self):
        with self.assertRaises(Lesson.DoesNotExist):
            self.build_manager().get('nonexistent-slug')

    def test_all(self):
        out = self.build_manager().all()
        self.assertEquals(out, [
            Lesson(
                'slug-2',
                LessonHeader('Earlier Lesson (alphabetically)', '<p>Contents</p>'),
                [
                    LessonSection('Foo', '<p>bar</p>', [
                        LessonSectionStep('Step One'),
                        LessonSectionStep('Step Two'),
                    ])
                ]
            ),
            Lesson(
                'slug-1',
                LessonHeader('Lesson', '<p>Contents</p>'),
                [
                    LessonSection('Foo', '<p>bar</p>', [
                        LessonSectionStep('Step One'),
                        LessonSectionStep('Step Two'),
                    ])
                ]
            )
        ])

    def test_all_parse_error(self):
        manager = self.build_manager(path=os.path.join(os.path.dirname(__file__), 'broken-lesson'))
        with self.assertRaisesMessage(LessonParseError, 'Lesson HTML needs a top-level <header>'):
            manager.all()
