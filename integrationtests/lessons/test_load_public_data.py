from integrationtests.lessons import LessonTest

class TestLesson(LessonTest):
    def test_lesson(self):
        b = self.browser
        b.visit('/lessons/')
        b.click_whatever('h2', text='I. Load public data and make a chart', wait=True)

        self.import_module('columnchart')
        self.import_module('filter')

        # 1. Introduction
        self.expect_highlight_next()
        self.click_next()

        # 2. 1. Load Public Data by URL
        self.expect_highlight(0)
        self.add_wf_module('Add from URL')

        self.expect_highlight(
            1,
            '.wf-module[data-module-name="Add from URL"]',
        )
        b.fill_in(
            'url',
            'https://app.workbenchdata.com/static/data/affordable_housing_lesson_1.csv',
            wait=True # wait for module to load
        )
        b.click_whatever('h2') # AAAAH! we need to blur, _then_ click Update!
        b.click_button('Update')

        # Wait for table to load
        self.expect_highlight(2, 'button.edit-note', wait=True)
        b.click_button('Edit Note')
        b.fill_in('notes', 'Data from datasf.org')
        b.click_whatever('h2') # blur, to commit data

        # wait for note to be set
        self.expect_highlight(3, 'i.context-collapse-button', wait=True)
        b.click_whatever('i.context-collapse-button')

        self.expect_highlight_next()
        self.click_next()

        # 3. 2. Make a column chart
        self.expect_highlight(0)
        self.add_wf_module('Column Chart')

        self.expect_highlight(1, '.wf-module[data-module-name="Column Chart"]')
        b.fill_in('title', 'a title', wait=True) # wait for module to load
        b.click_whatever('h2') # blur, to commit data

        self.expect_highlight_next()
        self.click_next()

        # 4. 3. Filter with a condition
        self.expect_highlight(0)
        self.add_wf_module('Filter', position=1)

        self.expect_highlight(1, '.wf-module[data-module-name="Filter"]')
        b.select('column', 'affordable_units', wait=True) # wait for module load
        b.select('condition', 'Greater than')
        b.fill_in('value', 200)
        b.click_whatever('h2') # blur, to commit data

        self.expect_highlight(2, '.wf-module[data-module-name="Column Chart"]')
        # bug in the test: it's hard to click the column chart without changing
        # anything. But we'll try.
        b.click_whatever(
            '.wf-module[data-module-name="Column Chart"] input[name="title"]'
        )

        b.assert_no_element('.lesson-highlight')
