from django.test import SimpleTestCase
from server.models.Lesson import Lesson, LessonHeader, LessonSection, LessonSectionStep, LessonParseError

class LessonTests(SimpleTestCase):
    def test_parse_header_in_html_body(self):
        out = Lesson.parse('a-stub', '<html><body><header><h1>Lesson</h1><p>p1</p><p>p2</p></header></body></html>')
        self.assertEquals(out, Lesson('a-stub', LessonHeader('Lesson', '<p>p1</p><p>p2</p>'), []))

    def test_parse_step(self):
        out = Lesson.parse('a-stub', '<header><h1>Lesson</h1><p>Contents</p></header><section><h2>Foo</h2><p>bar</p><ol class="steps"><li>1</li></ol></section>')
        self.assertEquals(out,
            Lesson(
                'a-stub',
                LessonHeader('Lesson', '<p>Contents</p>'),
                [ LessonSection('Foo', '<p>bar</p>', [ LessonSectionStep('1') ]) ]
            )
        )

    def test_parse_no_header(self):
        with self.assertRaisesMessage(LessonParseError, 'Lesson HTML needs a top-level <header>'):
            Lesson.parse('a-stub', '<h1>Foo</h1><p>body</p>')

    def test_parse_no_header_title(self):
        with self.assertRaisesMessage(LessonParseError, 'Lesson <header> needs a non-empty <h1> title'):
            Lesson.parse('a-stub', '<header><p>Contents</p></header>')

    def test_parse_no_section_title(self):
        with self.assertRaisesMessage(LessonParseError, 'Lesson <section> needs a non-empty <h2> title'):
            Lesson.parse('a-stub', '<header><h1>x</h1><p>y</p></header><section><ol class="steps"><li>foo</li></ol></section>')

    def test_parse_no_section_steps(self):
        with self.assertRaisesMessage(LessonParseError, 'Lesson <section> needs a non-empty <ol class="steps">'):
            Lesson.parse('a-stub', '<header><h1>x</h1><p>y</p></header><section><h2>title</h2><ol class="not-steps"><li>foo</li></ol></section>')
