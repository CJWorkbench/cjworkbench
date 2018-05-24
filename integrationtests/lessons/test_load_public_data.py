from integrationtests.lessons import LessonTest

class TestLesson(LessonTest):
    def test_lesson(self):
        b = self.browser
        b.visit('/lessons/')
        b.click_whatever('h2', text='I. Load public data and make a chart', wait=True)

        self.import_module('columnchart')

        # 1. Introduction
        self.expect_highlight_next()
        self.click_next()

        # 2. 1. Load Public Data by URL
        self.expect_highlight(0, '[data-module-name="Add from URL"]')
        b.click_whatever('[data-module-name="Add from URL"]')

        self.expect_highlight(1, '.wf-module[data-module-name="Add from URL"]')
