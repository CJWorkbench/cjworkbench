import json
import os.path
from django.test import SimpleTestCase
from server.models.lesson import (
    Lesson,
    LessonFooter,
    LessonHeader,
    LessonInitialWorkflow,
    LessonManager,
    LessonParseError,
    LessonSection,
    LessonSectionStep,
)


def _lesson_html_with_initial_workflow(initial_workflow_json):
    """
    Build lesson that is all valid except maybe `initial_workflow_json`.

    `initial_workflow_json` must be HTML-escaped for use in a <script> tag.
    """
    return ''.join([
        '<header><h1>x</h1></header>',
        '<script id="initialWorkflow" type="application/json">',
        initial_workflow_json,
        '</script>',
        '<section><h2>title</h2><p class="not-steps">content</p></section>',
        '<footer><h2>z</h2></footer>',
    ])


class LessonTests(SimpleTestCase):
    def test_parse_header_in_html_body(self):
        out = Lesson.parse('a-slug', """
            <html><body>
                <header><h1>Lesson</h1><p>p1</p><p>p2</p></header>
                <footer><h2>Foot</h2></footer>
            </body></html>
        """)
        self.assertEquals(out.header,
                          LessonHeader('Lesson', '<p>p1</p><p>p2</p>'))

    def test_parse_step(self):
        out = Lesson.parse('a-slug', """
            <header><h1>Lesson</h1><p>Contents</p></header>
            <section><h2>Foo</h2><p>bar</p><ol class="steps">
                <li data-highlight=\'[{"type":"Foo"}]\' data-test="true">1</li>
                <li data-highlight=\'[{"type":"Bar"}]\' data-test="0">2</li>
            </ol></section>
            <footer><h2>Foot</h2></footer>
        """)
        self.assertEquals(
            out.sections[0].steps,
            [
                LessonSectionStep('1', [{'type': 'Foo'}], 'true'),
                LessonSectionStep('2', [{'type': 'Bar'}], '0'),
            ]
        )

    def test_parse_invalid_step_highlight_json(self):
        with self.assertRaisesMessage(LessonParseError,
                                      'data-highlight contains invalid JSON'):
            Lesson.parse('a-slug', """
                <header><h1>X</h1><p>X</p></header>
                <section><h2>X</h2><p>bar</p><ol class="steps">
                    <li data-highlight=\'[{]\' data-test="true">1</li>
                </ol></section>
            """)

    def test_parse_missing_step_test(self):
        with self.assertRaisesMessage(
            LessonParseError,
            'missing data-test attribute, which must be JavaScript'
        ):
            Lesson.parse('a-slug', """
                <header><h1>Lesson</h1><p>Contents</p></header>
                <section><h2>Foo</h2><p>bar</p><ol class="steps">
                    <li data-highlight="[]">1</li>
                </ol></section>
            """)

    def test_parse_no_header(self):
        with self.assertRaisesMessage(
            LessonParseError,
            'Lesson HTML needs a top-level <header>'
        ):
            Lesson.parse('a-slug', '<h1>Foo</h1><p>body</p>')

    def test_parse_no_header_title(self):
        with self.assertRaisesMessage(
            LessonParseError,
            'Lesson <header> needs a non-empty <h1> title'
        ):
            Lesson.parse('a-slug', '<header><p>Contents</p></header>')

    def test_parse_no_section_title(self):
        with self.assertRaisesMessage(
            LessonParseError,
            'Lesson <section> needs a non-empty <h2> title'
        ):
            Lesson.parse('a-slug', """
                <header><h1>x</h1><p>y</p></header>
                <section><ol class="steps">
                    <li data-test="true">foo</li>
                </ol></section>
            """)

    def test_parse_no_section_steps(self):
        out = Lesson.parse('a-slug', """
            <header><h1>x</h1><p>y</p></header>
            <section><h2>T</h2><ol class="not-steps"><li>L</li></ol></section>
            <footer><h2>Foot</h2></footer>
        """)
        self.assertEquals(
            out.sections[0],
            LessonSection('T', '<ol class="not-steps"><li>L</li></ol>',
                          [], is_full_screen=False)
        )

    def test_parse_no_sections(self):
        """A lesson may be footer-only."""
        result = Lesson.parse('a-slug', """
            <header><h1>x</h1><p>y</p></header>
            <footer><h2>Foot</h2></footer>
        """)
        self.assertEquals(result.sections, [])

    def test_parse_fullscreen_section(self):
        result = Lesson.parse('a-slug', """
            <header><h1>x</h1></header>
            <section class="fullscreen"><h2>title</h2><p>content</p></section>
            <section><h2>title</h2><p>content</p></section>
            <footer><h2>z</h2></footer>
        """)
        self.assertTrue(result.sections[0].is_full_screen)
        self.assertFalse(result.sections[1].is_full_screen)

    def test_parse_nested_fullscreen_does_not_count(self):
        result = Lesson.parse('a-slug', """
            <header><h1>x</h1></header>
            <section><h2>T</h2><p class="fullscreen"></p></section>
            <footer><h2>z</h2></footer>
        """)
        self.assertFalse(result.sections[0].is_full_screen)

    def test_parse_fullscreen_footer(self):
        result = Lesson.parse('a-slug', """
            <header><h1>x</h1></header>
            <footer class="fullscreen"><h2>z</h2></footer>
        """)
        self.assertTrue(result.footer.is_full_screen)

    def test_parse_no_footer(self):
        with self.assertRaisesMessage(
            LessonParseError,
            'Lesson HTML needs a top-level <footer>'
        ):
            Lesson.parse('a-slug', """
                <header><h1>x</h1><p>y</p></header>
            """)

    def test_parse_no_footer_title(self):
        with self.assertRaisesMessage(
            LessonParseError,
            'Lesson <footer> needs a non-empty <h2> title'
        ):
            Lesson.parse('a-slug', """
                <header><h1>x</h1><p>y</p></header>
                <footer>Hi</footer>
            """)

    def test_parse_footer(self):
        out = Lesson.parse('a-slug', """
            <header><h1>x</h1><p>y</p></header>
            <footer><h2>Foot</h2><p>My foot</p></footer>
        """)
        self.assertEquals(out.footer, LessonFooter('Foot', '<p>My foot</p>'))

    def test_parse_initial_workflow(self):
        initial_workflow = {
            'tabs': [
                {
                    'name': 'Tab 1',
                    'wfModules': [
                        {
                            'module': 'loadurl',
                            'params': {
                                'url': 'http://foo.com',
                                'has_header': True,
                            },
                        },
                    ],
                },
            ],
        }
        out = Lesson.parse('a-slug', _lesson_html_with_initial_workflow(
            json.dumps(initial_workflow)
        ))
        self.assertEquals(
            out.initial_workflow,
            LessonInitialWorkflow(initial_workflow['tabs'])
        )

    def test_parse_initial_workflow_bad_json(self):
        with self.assertRaisesMessage(
            LessonParseError,
            'Initial-workflow YAML parse error'
        ):
            Lesson.parse('a-slug', _lesson_html_with_initial_workflow('{bad'))

    def test_parse_initial_workflow_yaml(self):
        out = Lesson.parse('a-slug', _lesson_html_with_initial_workflow("""
            tabs:
              - name: Tab 1
                wfModules:
                  - module: loadurl
                    params:
                        url: 'http://foo.com'
                        has_header: true
        """))
        self.assertEquals(
            out.initial_workflow,
            LessonInitialWorkflow([
                {
                    'name': 'Tab 1',
                    'wfModules': [
                        {
                            'module': 'loadurl',
                            'params': {
                                'url': 'http://foo.com',
                                'has_header': True,
                            },
                        },
                    ],
                },
            ])
        )


class LessonManagerTests(SimpleTestCase):
    def build_manager(self, path=None):
        if path is None:
            path = os.path.join(os.path.dirname(__file__), 'lessons')

        return LessonManager(path)

    def test_get(self):
        out = self.build_manager().get('slug-1')
        self.assertEquals(
            out,
            Lesson(
                'slug-1',
                LessonHeader('Lesson', '<p>Contents</p>'),
                [
                    LessonSection('Foo', '<p>bar</p>', [
                        LessonSectionStep('Step One', [], 'true'),
                        LessonSectionStep('Step Two', [], 'false'),
                    ])
                ],
                LessonFooter('Foot', '<p>Footer</p>')
            )
        )

    def test_get_parse_error(self):
        manager = self.build_manager(
            path=os.path.join(os.path.dirname(__file__), 'broken-lesson')
        )
        with self.assertRaisesMessage(
            LessonParseError,
            'Lesson HTML needs a top-level <header>'
        ):
            manager.get('slug-1')

    def test_get_does_not_exist(self):
        with self.assertRaises(Lesson.DoesNotExist):
            self.build_manager().get('nonexistent-slug')

    def test_get_hidden(self):
        result = self.build_manager().get('hidden-slug')
        self.assertEquals(result.title, 'Hidden Lesson')

    def test_all(self):
        out = self.build_manager().all()
        self.assertEquals(out, [
            Lesson(
                'slug-2',
                LessonHeader('Earlier Lesson (alphabetically)',
                             '<p>Contents</p>'),
                [
                    LessonSection('Foo', '<p>bar</p>', [
                        LessonSectionStep('Step One', [], 'true'),
                        LessonSectionStep('Step Two', [], 'false'),
                    ])
                ],
                LessonFooter('Foot', '<p>Footer</p>')
            ),
            Lesson(
                'slug-1',
                LessonHeader('Lesson', '<p>Contents</p>'),
                [
                    LessonSection('Foo', '<p>bar</p>', [
                        LessonSectionStep('Step One', [], 'true'),
                        LessonSectionStep('Step Two', [], 'false'),
                    ])
                ],
                LessonFooter('Foot', '<p>Footer</p>')
            )
        ])

    def test_all_parse_error(self):
        manager = self.build_manager(
            path=os.path.join(os.path.dirname(__file__), 'broken-lesson')
        )
        with self.assertRaisesMessage(
            LessonParseError,
            'Lesson HTML needs a top-level <header>'
        ):
            manager.all()
