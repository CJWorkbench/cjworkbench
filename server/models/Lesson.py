from enum import Enum
from io import StringIO
from xml.etree import ElementTree
import html5lib

def _build_inner_html(el):
    """
    Returns HTML of a xml.etree.ElementTree.
    """
    outer_html = ElementTree.tostring(el, encoding='unicode', method='html', short_empty_elements=True)
    open_tag_end = outer_html.index('>')
    close_tag_begin = outer_html.rindex('<')
    inner_html = outer_html[open_tag_end+1 : close_tag_begin]

    return inner_html

# A Lesson is a guide that helps the user build a Workflow we recommend.
#
# We implement Lessons in HTML, so they're stored as code, not in the database.
# This interface mimics django.db.models.Model.
class Lesson:
    def __init__(self, stub, header, sections):
        self.stub = stub
        self.header = header
        self.sections = sections

    def __eq__(self, other):
        return (self.stub, self.header, self.sections) == (other.stub, other.header, other.sections)

    def __repr__(self):
        return 'Lesson' + repr((self.stub, self.header, self.sections))

    @staticmethod
    def parse(stub, html):
        parser = html5lib.HTMLParser(strict=False, namespaceHTMLElements=False)
        root = parser.parse(StringIO(html))

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
        lesson_sections = list(LessonSection._from_etree(el) for el in section_els)

        return Lesson(stub, lesson_header, lesson_sections)

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
            raise LessonParseError('Lesson <header> needs a non-empty <h1> title')
        title = title_el.text

        # Now get the rest of the HTML, minus the <h1>
        el.remove(title_el) # hacky mutation
        html = _build_inner_html(el)

        return LessonHeader(title, html)

class LessonSection:
    def __init__(self, title, html, steps):
        self.title = title
        self.html = html
        self.steps = steps

    def __eq__(self, other):
        return (self.title, self.html, self.steps) == (other.title, other.html, other.steps)

    def __repr__(self):
        return 'LessonSection' + repr((self.title, self.html, self.steps))

    @staticmethod
    def _from_etree(el):
        title_el = el.find('./h2')
        if title_el is None or not title_el.text:
            raise LessonParseError('Lesson <section> needs a non-empty <h2> title')
        title = title_el.text

        steps_el = el.find('./ol[@class="steps"]')
        if steps_el is None or not steps_el:
            raise LessonParseError('Lesson <section> needs a non-empty <ol class="steps">')
        steps = list(LessonSectionStep._from_etree(el) for el in steps_el)

        # Now get the rest of the HTML, minus the <h1> and <ol>
        el.remove(title_el) # hacky mutation
        el.remove(steps_el) # hacky mutation
        html = _build_inner_html(el)

        return LessonHeader(title, html)

class LessonSectionStep:
    def __init__(self, html):
        self.html = html

    def __eq__(self, other):
        return (self.html,) == (other.html,)

    def __repr__(self):
        return 'LessonSectionStep' + repr((self.title, self.html))

    @staticmethod
    def _from_etree(el):
        html = _build_inner_html(el)
        LessonSectionStep(html)

class LessonParseError(Exception):
    def __init__(self, message):
        self.message = message
