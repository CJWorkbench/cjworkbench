from __future__ import annotations

from dataclasses import dataclass, field
import json
import pathlib
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree
import yaml
from django.conf import settings
import html5lib
import jsonschema
from itertools import groupby


# Load and parse the spec that defines the format of the initial workflow JSON
_initial_workflow_validator = jsonschema.Draft7Validator(
    yaml.safe_load(
        (
            pathlib.Path(__file__).parent / "lesson_initial_workflow_schema.yaml"
        ).read_text()
    ),
    format_checker=jsonschema.FormatChecker(),
)


def _build_inner_html(el: ElementTree, base_href: str) -> str:
    """
    Extract HTML text from a xml.etree.ElementTree.

    Beware: this mutates `el`:

        * It modifies img src starting with `./` to start with `{base_href}/`
        * It prepends STATIC_URL to img src
        * It replaces `{{LESSON_FILES_URL}}` with
          `{LESSON_FILES_URL}/{base_href}` (Assumes `base_href` has no reserved
          HTML characters.)

    Params:

        el: the `xml.etree.ElementTree` we want to dump
        base_href: if image URLs begin with './', what text to prepend
    """
    for img in el.findall(".//img"):
        src = img.get("src")
        if src.startswith("./"):
            src = f"{base_href}{src[1:]}"  # include the '/'
        if "//" not in src:
            src = f"{settings.STATIC_URL}{src}"
        img.set("src", src)

    outer_html = ElementTree.tostring(
        el, encoding="unicode", method="html", short_empty_elements=True
    )
    open_tag_end = outer_html.index(">")
    close_tag_begin = outer_html.rindex("<")
    inner_html = outer_html[(open_tag_end + 1) : close_tag_begin]
    inner_html = inner_html.replace(
        "{{LESSON_FILES_URL}}", f"{settings.LESSON_FILES_URL}/{base_href}"
    )

    return inner_html


@dataclass(frozen=True)
class LessonHeader:
    title: str = ""
    html: str = ""

    @classmethod
    def _from_etree(cls, el: ElementTree, base_href: str) -> LessonHeader:
        title_el = el.find("./h1")
        if title_el is None or not title_el.text:
            raise LessonParseError("Lesson <header> needs a non-empty <h1> title")
        title = title_el.text

        # Now get the rest of the HTML, minus the <h1>
        el.remove(title_el)  # hacky mutation
        html = _build_inner_html(el, base_href)

        return cls(title, html)


@dataclass(frozen=True)
class LessonInitialWorkflow:
    """
    The workflow a user should see the first time he/she opens a lesson.
    """

    tabs: List[Dict[str, Any]] = field(
        default_factory=lambda: [{"name": "Tab 1", "wfModules": []}]
    )

    @classmethod
    def _from_etree(cls, el: ElementTree):
        text = el.text
        try:
            jsondict = yaml.safe_load(text)
        except yaml.YAMLError as err:
            raise LessonParseError("Initial-workflow YAML parse error: " + str(err))
        try:
            _initial_workflow_validator.validate(jsondict)
        except jsonschema.ValidationError as err:
            raise LessonParseError("Initial-workflow structure is invalid: " + str(err))
        return cls(jsondict["tabs"])


@dataclass(frozen=True)
class LessonSectionStep:
    html: str = ""
    highlight: str = ""
    test_js: str = ""
    """
    "Test" JavaScript that determines whether the step is complete.

    When parsing HTML, LessonSectionStep will replace `{{LESSON_FILES_URL}}`
    with the lesson-files URL. So you can write a test like:

        return (
            workflow.tabs[0].wfModules[0].params.url
            === '{{LESSON_FILES_URL}}/x.csv'
        )

    Workbench's lesson system will only run a step's test code if all, given
    the current store, all tests leading up to it pass.
    """

    @classmethod
    def _from_etree(cls, el: ElementTree, base_href: str) -> LessonSectionStep:
        html = _build_inner_html(el, base_href)

        highlight_s = el.get("data-highlight")
        if not highlight_s:
            highlight_s = "[]"
        try:
            highlight = json.loads(highlight_s)
        except json.decoder.JSONDecodeError:
            raise LessonParseError("data-highlight contains invalid JSON")

        test_js = el.get("data-test")
        if not test_js:
            raise LessonParseError(
                "missing data-test attribute, which must be JavaScript"
            )
        test_js = test_js.replace(
            "{{LESSON_FILES_URL}}", f"{settings.LESSON_FILES_URL}/{base_href}"
        )

        return cls(html, highlight, test_js)


@dataclass(frozen=True)
class LessonSection:
    title: str = ""
    html: str = ""
    steps: List[LessonSectionStep] = field(default_factory=list)
    is_full_screen: bool = False

    @classmethod
    def _from_etree(cls, el: ElementTree, base_href: str) -> LessonSection:
        title_el = el.find("./h2")
        if title_el is None or not title_el.text:
            raise LessonParseError("Lesson <section> needs a non-empty <h2> title")
        title = title_el.text

        steps_el = el.find('./ol[@class="steps"]')
        if steps_el is None or not steps_el:
            steps = list()
        else:
            steps = [LessonSectionStep._from_etree(el, base_href) for el in steps_el]

        # Now get the rest of the HTML, minus the <h1> and <ol>
        el.remove(title_el)  # hacky mutation
        if steps_el is not None:
            el.remove(steps_el)  # hacky mutation
        html = _build_inner_html(el, base_href)

        # Look for "fullscreen" class on section, set fullscreen flag if so
        is_full_screen = el.find('[@class="fullscreen"]') is not None

        return cls(title, html, steps, is_full_screen)


@dataclass(frozen=True)
class LessonFooter:
    """
    The last "section" of a lesson: appears after all LessonSections.

    It's not included in the "page 1 of 4" count.

    It has confetti!
    """

    title: str = ""
    html: str = ""
    is_full_screen: bool = False

    @classmethod
    def _from_etree(cls, el: ElementTree, base_href: str) -> LessonFooter:
        title_el = el.find("./h2")
        if title_el is None or not title_el.text:
            raise LessonParseError("Lesson <footer> needs a non-empty <h2> title")
        title = title_el.text
        is_full_screen = el.find('[@class="fullscreen"]') is not None

        # Now get the rest of the HTML, minus the <h2>
        el.remove(title_el)  # hacky mutation
        html = _build_inner_html(el, base_href)

        return cls(title, html, is_full_screen)


class LessonParseError(Exception):
    pass


# A Lesson is a guide that helps the user build a Workflow we recommend.
#
# We implement Lessons in HTML, so they're stored as code, not in the database.
# This interface mimics django.db.models.Model.
@dataclass(frozen=True)
class Lesson:
    course: Optional["Course"]
    slug: str
    locale_id: str
    header: LessonHeader = LessonHeader()
    sections: List[LessonSection] = field(default_factory=list)
    footer: LessonFooter = LessonFooter()
    initial_workflow: LessonInitialWorkflow = LessonInitialWorkflow()

    @property
    def title(self):
        return self.header.title

    @classmethod
    def load_from_path(cls, course: Optional["Course"], path: pathlib.Path) -> Lesson:
        slug = path.stem
        locale_id = path.parent.stem
        html = path.read_text()
        try:
            return cls.parse(course, slug, locale_id, html)
        except LessonParseError as err:
            raise LessonParseError("In %s: %s" % (str(path), str(err)))

    @classmethod
    def parse(
        cls, course: Optional["Course"], slug: str, locale_id: str, html: str
    ) -> Lesson:
        if course:
            base_href = f"courses/{locale_id}/{course.slug}/{slug}"
        else:
            base_href = f"lessons/{locale_id}/{slug}"

        parser = html5lib.HTMLParser(strict=True, namespaceHTMLElements=False)
        try:
            root: ElementTree = parser.parseFragment(html)
        except html5lib.html5parser.ParseError as err:
            raise LessonParseError(
                "HTML error on line %d, column %d: %s"
                % (parser.errors[0][0][0], parser.errors[0][0][1], str(err))
            )

        header_el = root.find("./header")
        if header_el is None:
            raise LessonParseError("Lesson HTML needs a top-level <header>")
        lesson_header = LessonHeader._from_etree(header_el, base_href)

        section_els = root.findall("./section")
        lesson_sections = list(
            LessonSection._from_etree(el, base_href) for el in section_els
        )

        footer_el = root.find("./footer")
        if footer_el is None:
            raise LessonParseError("Lesson HTML needs a top-level <footer>")
        lesson_footer = LessonFooter._from_etree(footer_el, base_href)

        initial_workflow_el = root.find('./script[@id="initialWorkflow"]')
        if initial_workflow_el is None:
            # initial workflow is optional, blank wf if missing
            lesson_initial_workflow = LessonInitialWorkflow()
        else:
            lesson_initial_workflow = LessonInitialWorkflow._from_etree(
                initial_workflow_el
            )

        return cls(
            course,
            slug,
            locale_id,
            lesson_header,
            lesson_sections,
            lesson_footer,
            lesson_initial_workflow,
        )

    class DoesNotExist(Exception):
        pass


AllLessons = [
    Lesson.load_from_path(None, path)
    for path in ((pathlib.Path(__file__).parent.parent).glob("lessons/*/*.html"))
]
AllLessonsByLocale = {
    locale_id: sorted(lessons, key=lambda lesson: lesson.header.title)
    for locale_id, lessons in groupby(
        sorted(AllLessons, key=lambda lesson: lesson.locale_id),
        lambda lesson: lesson.locale_id,
    )
}

LessonLookup = dict(
    (lesson.locale_id + "/" + lesson.slug, lesson) for lesson in AllLessons
)
# add "hidden" lessons to LessonLookup. They do not appear in AllLessons.
for _path in (pathlib.Path(__file__).parent.parent).glob("lessons/hidden/*/*.html"):
    lesson = Lesson.load_from_path(None, _path)
    LessonLookup[lesson.locale_id + "/" + lesson.slug] = lesson
