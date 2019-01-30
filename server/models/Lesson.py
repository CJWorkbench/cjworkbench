from io import StringIO
import json
import os.path
import pathlib
from typing import List
from xml.etree import ElementTree
from django.conf import settings
import html5lib
import jsonschema
import yaml


# Load and parse the spec that defines the format of the initial workflow JSON, once
_SpecPath = os.path.join(os.path.dirname(__file__), 'lesson_initial_workflow_schema.yaml')
with open(_SpecPath, 'rt') as spec_file:
    _SpecSchema = yaml.load(spec_file)
_initial_workflow_validator = jsonschema.Draft7Validator(
    _SpecSchema,
    format_checker=jsonschema.FormatChecker()
)

def _build_inner_html(el):
    """Extract HTML text from a xml.etree.ElementTree."""
    outer_html = ElementTree.tostring(el, encoding='unicode', method='html',
                                      short_empty_elements=True)
    open_tag_end = outer_html.index('>')
    close_tag_begin = outer_html.rindex('<')
    inner_html = outer_html[(open_tag_end + 1):close_tag_begin]

    # HACK: lessons can have <img> tags, which are always relative. Make them
    # point to staticfiles. This hack will bite us sometime, but [2018-10-02]
    # things are hectic today and future pain costs less than today's pain.
    #
    # Of course, the _correct_ way to do this would be through the element tree
    # -- which we already have. TODO rewrite to use the element tree.
    inner_html = inner_html.replace('src="', 'src="' + settings.STATIC_URL)

    return inner_html


# a fake django.db.models.Manager that reads from the filesystem
class LessonManager:
    def __init__(self, path):
        self.path = path

    def _get(self, slug, path) -> 'Lesson':
        """
        Parse the lesson at `path` or raises FileNotFoundError.
        """
        with open(path, 'r', encoding='utf-8') as f:
            return Lesson.parse(slug, f.read())

    def get(self, slug) -> 'Lesson':
        """
        Find and load the lesson `slug`.

        Raise Lesson.DoesNotExist() on invalid slug.
        """
        path = os.path.join(self.path, slug + '.html')
        try:
            return self._get(slug, path)
        except FileNotFoundError:
            # Maybe it's in the hidden/ directory? That's where we put lessons
            # that we won't list in self.all().
            hidden_path = os.path.join(self.path, 'hidden', slug + '.html')
            try:
                return self._get(slug, hidden_path)
            except FileNotFoundError:
                raise Lesson.DoesNotExist()

    def all(self) -> List['Lesson']:
        """
        List non-hidden lessons, sorted alphabetically.
        """
        ret = []

        for html_path in pathlib.Path(self.path).glob('*.html'):
            slug = html_path.stem
            if slug[0] != '_':
                ret.append(self.get(slug))

        ret.sort(key=lambda lesson: lesson.header.title)

        return ret


# A Lesson is a guide that helps the user build a Workflow we recommend.
#
# We implement Lessons in HTML, so they're stored as code, not in the database.
# This interface mimics django.db.models.Model.
class Lesson:
    def __init__(self, slug, header, sections, footer, initial_workflow=None):
        self.slug = slug
        self.header = header
        self.sections = sections
        self.footer = footer
        self.initial_workflow = initial_workflow

    def __eq__(self, other):
        return (self.slug, self.header, self.sections) == \
                (other.slug, other.header, other.sections)

    def __repr__(self):
        return 'Lesson' + repr((self.slug, self.header, self.sections))

    def get_absolute_url(self):
        return '/lessons/%s/' % self.slug

    @property
    def title(self):
        return self.header.title

    @staticmethod
    def parse(slug, html):
        parser = html5lib.HTMLParser(strict=False, namespaceHTMLElements=False)
        root = parser.parse(StringIO(html))  # this is an xml.etree.ElementTree

        # HTML may have <html> and <body> tags. If so, navigate within. We only
        # care about the body.
        body = root.find('.//body')
        if body:
            root = body

        header_el = root.find('./header')
        if header_el is None:
            raise LessonParseError('Lesson HTML needs a top-level <header>')
        lesson_header = LessonHeader._from_etree(header_el)

        section_els = root.findall('./section')
        lesson_sections = list(LessonSection._from_etree(el)
                               for el in section_els)

        footer_el = root.find('./footer')
        if footer_el is None:
            raise LessonParseError('Lesson HTML needs a top-level <footer>')
        lesson_footer = LessonFooter._from_etree(footer_el)

        initial_workflow_el = root.find('./script[@id="initialWorkflow"]')
        if initial_workflow_el is None:
            lesson_initial_workflow = None  # initial workflow is optional, blank wf if missing
        else:
            lesson_initial_workflow = LessonInitialWorkflow._from_etree(initial_workflow_el)

        return Lesson(slug, lesson_header, lesson_sections, lesson_footer, lesson_initial_workflow)

    class DoesNotExist(Exception):
        pass

    # fake django.db.models.Manager
    objects = LessonManager(os.path.join(settings.BASE_DIR, 'server',
                                         'lessons'))


class LessonHeader:
    def __init__(self, title, html):
        self.title = title
        self.html = html

    def __eq__(self, other):
        return (self.title, self.html) == (other.title, other.html)

    def __repr__(self):
        return 'LessonHeader' + repr((self.title, self.html))

    @staticmethod
    def _from_etree(el):
        title_el = el.find('./h1')
        if title_el is None or not title_el.text:
            raise LessonParseError(
                'Lesson <header> needs a non-empty <h1> title'
            )
        title = title_el.text

        # Now get the rest of the HTML, minus the <h1>
        el.remove(title_el)  # hacky mutation
        html = _build_inner_html(el)

        return LessonHeader(title, html)


class LessonInitialWorkflow:
    def __init__(self, initial_tabs):
        self.tabs = initial_tabs  # a list of dicts, each describing a tab

    def __eq__(self, other):
        return self.tabs == other.tabs

    def __repr__(self):
        return 'LessonInitialWorkflow' + repr((self.initial_workflow,))

    @staticmethod
    def _from_etree(el):
        text = el.text
        try:
            jsondict = json.loads(text)
        except ValueError as e:
            raise LessonParseError(
                'Initial workflow json parse error: ' + str(e)
            )
        try:
            _initial_workflow_validator.validate(jsondict)
        except jsonschema.ValidationError as e:
            raise LessonParseError(
                'Initial workflow json validation error: ' + str(e)
            )
        return LessonInitialWorkflow(jsondict['tabs'])


class LessonSection:
    def __init__(self, title, html, steps, is_full_screen=False):
        self.title = title
        self.html = html
        self.steps = steps
        self.is_full_screen = is_full_screen

    def __eq__(self, other):
        return (self.title, self.html, self.steps, self.is_full_screen) == \
                (other.title, other.html, other.steps, other.is_full_screen)

    def __repr__(self):
        return 'LessonSection' + repr((self.title, self.html, self.steps, self.is_full_screen))

    @staticmethod
    def _from_etree(el):
        title_el = el.find('./h2')
        if title_el is None or not title_el.text:
            raise LessonParseError(
                'Lesson <section> needs a non-empty <h2> title'
            )
        title = title_el.text

        steps_el = el.find('./ol[@class="steps"]')
        if steps_el is None or not steps_el:
            steps = list()
        else:
            steps = list(LessonSectionStep._from_etree(el) for el in steps_el)

        # Now get the rest of the HTML, minus the <h1> and <ol>
        el.remove(title_el)  # hacky mutation
        if steps_el is not None:
            el.remove(steps_el)  # hacky mutation
        html = _build_inner_html(el)

        # Look for "fullscreen" class on section, set fullscreen flag if so
        full_screen_el = el.find('[@class="fullscreen"]')
        is_full_screen = full_screen_el is not None

        return LessonSection(title, html, steps, is_full_screen=is_full_screen)


class LessonSectionStep:
    def __init__(self, html, highlight, test_js):
        self.html = html
        self.highlight = highlight
        self.test_js = test_js

    def __eq__(self, other):
        return (self.html, self.highlight, self.test_js) == \
                (other.html, other.highlight, other.test_js)

    def __repr__(self):
        return ('LessonSectionStep'
                + repr((self.html, self.highlight, self.test_js)))

    @staticmethod
    def _from_etree(el):
        html = _build_inner_html(el)

        highlight_s = el.get('data-highlight')
        if not highlight_s:
            highlight_s = '[]'
        try:
            highlight = json.loads(highlight_s)
        except json.decoder.JSONDecodeError:
            raise LessonParseError('data-highlight contains invalid JSON')

        test_js = el.get('data-test')
        if not test_js:
            raise LessonParseError(
                'missing data-test attribute, which must be JavaScript'
            )

        return LessonSectionStep(html, highlight, test_js)


# The Footer is the last "section" which usually says "you finished the lesson" or something
# It is not included in the page count displayed in the nav bar, and it has confetti!
class LessonFooter:
    def __init__(self, title, html):
        self.title = title
        self.html = html

    def __eq__(self, other):
        return (self.title, self.html) == (other.title, other.html)

    def __repr__(self):
        return 'LessonFooter' + repr((self.title, self.html))

    @staticmethod
    def _from_etree(el):
        title_el = el.find('./h2')
        if title_el is None or not title_el.text:
            raise LessonParseError(
                'Lesson <footer> needs a non-empty <h2> title'
            )
        title = title_el.text

        # Now get the rest of the HTML, minus the <h2>
        el.remove(title_el)  # hacky mutation
        html = _build_inner_html(el)

        return LessonFooter(title, html)


class LessonParseError(Exception):
    def __init__(self, message):
        self.message = message
