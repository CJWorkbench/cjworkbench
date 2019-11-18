import json
from django.test import SimpleTestCase, override_settings
import unittest
from server.models.course import Course
from server.models.lesson import (
    AllLessons,
    Lesson,
    LessonFooter,
    LessonInitialWorkflow,
    LessonLookup,
    LessonParseError,
    LessonSection,
    LessonSectionStep,
)


def _lesson_html_with_initial_workflow(initial_workflow_json):
    """
    Build lesson that is all valid except maybe `initial_workflow_json`.

    `initial_workflow_json` must be HTML-escaped for use in a <script> tag.
    """
    return "".join(
        [
            "<header><h1>x</h1></header>",
            '<script id="initialWorkflow" type="application/json">',
            initial_workflow_json,
            "</script>",
            '<section><h2>title</h2><p class="not-steps">content</p></section>',
            "<footer><h2>z</h2></footer>",
        ]
    )


class LessonTests(SimpleTestCase):
    def test_parse_step(self):
        out = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>Lesson</h1><p>Contents</p></header>
            <section><h2>Foo</h2><p>bar</p><ol class="steps">
                <li data-highlight=\'[{"type":"Foo"}]\' data-test="true">1</li>
                <li data-highlight=\'[{"type":"Bar"}]\' data-test="0">2</li>
            </ol></section>
            <footer><h2>Foot</h2></footer>
        """,
        )
        self.assertEquals(
            out.sections[0].steps,
            [
                LessonSectionStep("1", [{"type": "Foo"}], "true"),
                LessonSectionStep("2", [{"type": "Bar"}], "0"),
            ],
        )

    def test_parse_invalid_step_highlight_json(self):
        with self.assertRaisesRegex(
            LessonParseError, "data-highlight contains invalid JSON"
        ):
            Lesson.parse(
                None,
                "a-slug",
                "en",
                """
                <header><h1>X</h1><p>X</p></header>
                <section><h2>X</h2><p>bar</p><ol class="steps">
                    <li data-highlight=\'[{]\' data-test="true">1</li>
                </ol></section>
            """,
            )

    def test_parse_missing_step_test(self):
        with self.assertRaisesRegex(
            LessonParseError, "missing data-test attribute, which must be JavaScript"
        ):
            Lesson.parse(
                None,
                "a-slug",
                "en",
                """
                <header><h1>Lesson</h1><p>Contents</p></header>
                <section><h2>Foo</h2><p>bar</p><ol class="steps">
                    <li data-highlight="[]">1</li>
                </ol></section>
            """,
            )

    @override_settings(LESSON_FILES_URL="https://files")
    def test_parse_section_step_lesson_files_url(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p>x</p></header>
            <section><h2>X</h2><ol class="steps">
                <li data-test="window.x == '{{LESSON_FILES_URL}}/x.csv'">X</li>
            </ol></section>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertEquals(
            result.sections[0].steps[0].test_js,
            "window.x == 'https://files/lessons/en/a-slug/x.csv'",
        )

    def test_parse_invalid_html(self):
        with self.assertRaisesRegex(
            LessonParseError, "HTML error on line 2, column 38: Unexpected end tag"
        ):
            Lesson.parse(
                None,
                "a-slug",
                "en",
                """
                <header><h1>Lesson</p></header>
            """,
            )

    def test_parse_no_header(self):
        with self.assertRaisesRegex(
            LessonParseError, "Lesson HTML needs a top-level <header>"
        ):
            Lesson.parse(None, "a-slug", "en", "<h1>Foo</h1><p>body</p>")

    def test_parse_no_header_title(self):
        with self.assertRaisesRegex(
            LessonParseError, "Lesson <header> needs a non-empty <h1> title"
        ):
            Lesson.parse(None, "a-slug", "en", "<header><p>Contents</p></header>")

    def test_parse_no_section_title(self):
        with self.assertRaisesRegex(
            LessonParseError, "Lesson <section> needs a non-empty <h2> title"
        ):
            Lesson.parse(
                None,
                "a-slug",
                "en",
                """
                <header><h1>x</h1><p>y</p></header>
                <section><ol class="steps">
                    <li data-test="true">foo</li>
                </ol></section>
            """,
            )

    def test_parse_no_section_steps(self):
        out = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p>y</p></header>
            <section><h2>T</h2><ol class="not-steps"><li>L</li></ol></section>
            <footer><h2>Foot</h2></footer>
        """,
        )
        self.assertEquals(
            out.sections[0],
            LessonSection(
                "T", '<ol class="not-steps"><li>L</li></ol>', [], is_full_screen=False
            ),
        )

    def test_parse_no_sections(self):
        """A lesson may be footer-only."""
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p>y</p></header>
            <footer><h2>Foot</h2></footer>
        """,
        )
        self.assertEquals(result.sections, [])

    def test_parse_fullscreen_section(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1></header>
            <section class="fullscreen"><h2>title</h2><p>content</p></section>
            <section><h2>title</h2><p>content</p></section>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertTrue(result.sections[0].is_full_screen)
        self.assertFalse(result.sections[1].is_full_screen)

    def test_parse_nested_fullscreen_does_not_count(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1></header>
            <section><h2>T</h2><p class="fullscreen"></p></section>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertFalse(result.sections[0].is_full_screen)

    def test_parse_fullscreen_footer(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1></header>
            <footer class="fullscreen"><h2>z</h2></footer>
        """,
        )
        self.assertTrue(result.footer.is_full_screen)

    def test_parse_no_footer(self):
        with self.assertRaisesRegex(
            LessonParseError, "Lesson HTML needs a top-level <footer>"
        ):
            Lesson.parse(
                None,
                "a-slug",
                "en",
                """
                <header><h1>x</h1><p>y</p></header>
            """,
            )

    def test_parse_no_footer_title(self):
        with self.assertRaisesRegex(
            LessonParseError, "Lesson <footer> needs a non-empty <h2> title"
        ):
            Lesson.parse(
                None,
                "a-slug",
                "en",
                """
                <header><h1>x</h1><p>y</p></header>
                <footer>Hi</footer>
            """,
            )

    def test_parse_footer(self):
        out = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p>y</p></header>
            <footer><h2>Foot</h2><p>My foot</p></footer>
        """,
        )
        self.assertEquals(out.footer, LessonFooter("Foot", "<p>My foot</p>"))

    @override_settings(STATIC_URL="//static/")
    def test_parse_header_relative_img_src_without_course(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p><img src="./foo.png"/></p></header>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertEquals(
            result.header.html, '<p><img src="//static/lessons/en/a-slug/foo.png"></p>'
        )

    @override_settings(STATIC_URL="//static/")
    def test_parse_header_relative_img_src_with_course(self):
        result = Lesson.parse(
            Course("a-course"),
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p><img src="./foo.png"/></p></header>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertEquals(
            result.header.html,
            '<p><img src="//static/courses/en/a-course/a-slug/foo.png"></p>',
        )

    @override_settings(LESSON_FILES_URL="https://files")
    def test_parse_header_lesson_files_url_with_course(self):
        result = Lesson.parse(
            Course("a-course"),
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p><i>{{LESSON_FILES_URL}}/x.csv</i></p></header>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertEquals(
            result.header.html,
            "<p><i>https://files/courses/en/a-course/a-slug/x.csv</i></p>",
        )

    @override_settings(LESSON_FILES_URL="https://files")
    def test_parse_header_lesson_files_url_without_course(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p><i>{{LESSON_FILES_URL}}/x.csv</i></p></header>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertEquals(
            result.header.html, "<p><i>https://files/lessons/en/a-slug/x.csv</i></p>"
        )

    @override_settings(STATIC_URL="//static/")
    def test_parse_header_absolute_img_src(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1><p><img src="images/foo.png"/></p></header>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertEquals(
            result.header.html, '<p><img src="//static/images/foo.png"></p>'
        )

    @override_settings(STATIC_URL="//static/")
    def test_parse_header_full_url_img_src(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1><img src="https://x/images/foo.png"/></header>
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertEquals(result.header.html, '<img src="https://x/images/foo.png">')

    @override_settings(STATIC_URL="//static/")
    def test_parse_section_relative_img_src(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1></header>
            '<section><h2>title</h2><p><img src="./foo.png"></p></section>',
            <footer><h2>z</h2></footer>
        """,
        )
        self.assertEquals(
            result.sections[0].html,
            '<p><img src="//static/lessons/en/a-slug/foo.png"></p>',
        )

    @override_settings(STATIC_URL="//static/")
    def test_parse_footer_relative_img_src(self):
        result = Lesson.parse(
            None,
            "a-slug",
            "en",
            """
            <header><h1>x</h1></header>
            <footer><h2>z</h2><p><img src="./foo.png"></p></footer>
        """,
        )
        self.assertEquals(
            result.footer.html, '<p><img src="//static/lessons/en/a-slug/foo.png"></p>'
        )

    def test_parse_initial_workflow(self):
        initial_workflow = {
            "tabs": [
                {
                    "name": "Tab 1",
                    "wfModules": [
                        {
                            "module": "loadurl",
                            "params": {"url": "http://foo.com", "has_header": True},
                            "collapsed": True,
                            "note": "You're gonna love this data!",
                        }
                    ],
                }
            ]
        }
        out = Lesson.parse(
            None,
            "a-slug",
            "en",
            _lesson_html_with_initial_workflow(json.dumps(initial_workflow)),
        )
        self.assertEquals(
            out.initial_workflow, LessonInitialWorkflow(initial_workflow["tabs"])
        )

    def test_parse_initial_workflow_bad_json(self):
        with self.assertRaisesRegex(
            LessonParseError, "Initial-workflow YAML parse error"
        ):
            Lesson.parse(
                None, "a-slug", "en", _lesson_html_with_initial_workflow("{bad")
            )

    def test_parse_initial_workflow_yaml(self):
        out = Lesson.parse(
            None,
            "a-slug",
            "en",
            _lesson_html_with_initial_workflow(
                """
                tabs:
                  - name: Tab 1
                    wfModules:
                      - module: loadurl
                        params:
                            url: 'http://foo.com'
                            has_header: true
            """
            ),
        )
        self.assertEquals(
            out.initial_workflow,
            LessonInitialWorkflow(
                [
                    {
                        "name": "Tab 1",
                        "wfModules": [
                            {
                                "module": "loadurl",
                                "params": {"url": "http://foo.com", "has_header": True},
                            }
                        ],
                    }
                ]
            ),
        )


class LessonGlobalsTests(unittest.TestCase):
    # These tests rely on the existence of a "hidden" lesson. Its existence
    # is pretty hairy; but [2019-02-28] it seems likely the "hidden" feature
    # will fall by the wayside if we don't keep an example in that directory
    # and test the "hidden lessons" feature with every deploy.
    HiddenSlug = "_hidden-example"
    HiddenLocale = "en"

    def test_hidden_lessons_not_in_AllLessons(self):
        self.assertFalse(any(l.slug == self.HiddenSlug for l in AllLessons))

    def test_hidden_lessons_appear_in_LessonLookup(self):
        self.assertIn(self.HiddenLocale + "/" + self.HiddenSlug, LessonLookup)
