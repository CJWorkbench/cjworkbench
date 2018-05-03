from django.conf import settings
from enum import Enum
from io import StringIO
import pathlib
from xml.etree import ElementTree
import html5lib
import os.path

def _build_inner_html(el):
    """
    Returns HTML of a xml.etree.ElementTree.
    """
    outer_html = ElementTree.tostring(el, encoding='unicode', method='html', short_empty_elements=True)
    open_tag_end = outer_html.index('>')
    close_tag_begin = outer_html.rindex('<')
    inner_html = outer_html[open_tag_end+1 : close_tag_begin]

    return inner_html

# a fake django.db.models.Manager that reads from the filesystem
class LessonManager:
    def __init__(self, path):
        self.path = path
        self._cache = {}
        self._all_cache = None # cached self.all() response

    def get(self, slug):
        path = os.path.join(self.path, slug + '.html')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return Lesson.parse(slug, f.read())
        except FileNotFoundError:
            raise Lesson.DoesNotExist()

    def all(self):
        """
        The list (not a QuerySet!) of all lessons, ordered alphabetically.
        """
        ret = []

        for html_path in pathlib.Path(self.path).glob('*.html'):
            slug = html_path.stem
            ret.append(self.get(slug))

        ret.sort(key=lambda lesson: lesson.header.title)

        return ret


# A Lesson is a guide that helps the user build a Workflow we recommend.
#
# We implement Lessons in HTML, so they're stored as code, not in the database.
# This interface mimics django.db.models.Model.
class Lesson:
    def __init__(self, slug, header, sections):
        self.slug = slug
        self.header = header
        self.sections = sections

    def __eq__(self, other):
        return (self.slug, self.header, self.sections) == (other.slug, other.header, other.sections)

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

        return Lesson(slug, lesson_header, lesson_sections)

    class DoesNotExist(Exception):
        pass

    # fake django.db.models.Manager
    objects = LessonManager(os.path.join(settings.BASE_DIR, 'server', 'lessons'))

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
            steps = list()
        else:
            steps = list(LessonSectionStep._from_etree(el) for el in steps_el)

        # Now get the rest of the HTML, minus the <h1> and <ol>
        el.remove(title_el) # hacky mutation
        if steps_el is not None: el.remove(steps_el) # hacky mutation
        html = _build_inner_html(el)

        return LessonSection(title, html, steps)

class LessonSectionStep:
    def __init__(self, html):
        self.html = html

    def __eq__(self, other):
        return (self.html,) == (other.html,)

    def __repr__(self):
        return 'LessonSectionStep' + repr((self.html,))

    @staticmethod
    def _from_etree(el):
        html = _build_inner_html(el)
        return LessonSectionStep(html)

class LessonParseError(Exception):
    def __init__(self, message):
        self.message = message
