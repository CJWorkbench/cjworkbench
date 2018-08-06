from integrationtests.lessons import LessonTest

DataUrl = 'https://app.workbenchdata.com/static/data/population_dirty_data.csv'


class TestLesson(LessonTest):
    def _rename_column(self, old: str, new: str) -> None:
        """Rename a column in the "Refine" wf-module."""
        # Refine.js has timing issues: it lets the user edit in between
        # saves, and then it overwrites the user's edits. But
        # [adamhooper, 2018-06-01] today is not the day to fix it.
        #
        # So how can we test that our edit succeeds? By waiting for the element
        # we just edited to disappear. It'll only disappear once the server
        # informs us of updates.
        self.browser.fill_in(f'rename[{old}]', new)
        self.browser.click_whatever('h2')  # blur, to force save
        self.browser.assert_no_element(f'input[name="rename[{old}]"]',
                                       wait=True)

    def test_lesson(self):
        b = self.browser
        b.visit('/lessons/')
        b.click_whatever('h2', text='II. Clean and standardize data',
                         wait=True)

        self.import_module('dropna')
        self.import_module('linechart')
        self.import_module('nulldropper')
        self.import_module('reshape')

        # 1. Introduction
        self.expect_highlight_next()
        self.click_next()

        # 2. 1. Dropping empty rows and columns
        self.expect_highlight(0, '.add-module-search')
        self.add_wf_module('Add from URL')

        # Wait for module to load
        self.expect_highlight(
            1,
            '.wf-module[data-module-name="Add from URL"]',
            wait=True
        )
        b.fill_in('url', DataUrl, wait=True)  # wait for module to load
        b.click_button('Update')

        # Wait for module to update
        self.expect_highlight(
            2,
            '.in-between-modules:last-child .add-module-search',
            wait=True
        )
        self.add_wf_module('Drop empty columns')

        # Wait for module to load
        self.expect_highlight(
            3,
            '.in-between-modules:last-child .add-module-search',
            wait=True
        )
        self.add_wf_module('Drop empty rows')

        # Wait for module to load
        self.expect_highlight(
            4,
            '.wf-module[data-module-name="Drop empty rows"]',
        )

        # Wait for checkboxes to load
        b.check('colnames[MetroArea]', wait=True)
        b.check('colnames[Population]')

        self.expect_highlight_next()
        self.click_next()

        # 3. 2. Standardize column values
        self.expect_highlight(
            0,
            '.in-between-modules:last-child .add-module-search'
        )
        self.add_wf_module('Refine')

        # Wait for module to load
        self.expect_highlight(
            1,
            '.wf-module[data-module-name="Refine"]',
            wait=True
        )

        # Wait for column to appear
        self.select_column('column', 'MetroArea')

        # Wait for module to update
        self.expect_highlight(
            1,  # still not done this step
            '.wf-module[data-module-name="Refine"]',
            wait=True
        )

        b.assert_element('input[name="rename[Seattle - Tacoma]"]', wait=True)
        self._rename_column(
            'San Jose-San Francisco-Oakland', 'San Francisco - Bay Area'
        )
        self.expect_highlight(1)  # not done this step
        self._rename_column('DallasFORTHWorth', 'Dallas - Fort Worth')

        # Okay, we're done now
        self.expect_highlight(2, '.wf-module[data-module-name="Refine"]')
        b.uncheck('selected[Denver - Aurora]')

        self.expect_highlight_next()
        self.click_next()

        # 3. Changing table format
        self.expect_highlight(
            0,
            '.in-between-modules:last-child .add-module-search'
        )
        self.add_wf_module('Reshape')

        # Wait for module to start loading
        self.expect_highlight(
            1,
            '.wf-module[data-module-name="Reshape"]',
            wait=True
        )
        # Wait for module to load
        b.select('direction', 'Long to wide', wait=True)

        # Wait for param change to register
        self.expect_highlight(
            2,
            '.wf-module[data-module-name="Reshape"]',
            wait=True
        )
        with b.scope('.wf-module[data-module-name="Reshape"]'):
            self.select_column('colnames', 'Year')

        # Wait for param change to register
        self.expect_highlight(
            3,
            '.wf-module[data-module-name="Reshape"]',
            wait=True
        )
        self.select_column('varcol', 'MetroArea')

        b.assert_no_element('.lesson-highlight')
