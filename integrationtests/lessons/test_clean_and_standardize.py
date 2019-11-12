from integrationtests.lessons import LessonTest


DataUrl = "https://storage.googleapis.com/production-static.workbenchdata.com/lessons/en/clean-and-standardize/population_growth_data.csv"


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
        self.browser.fill_in(f"rename[{old}]", new)
        self.browser.click_whatever("h2")  # blur, to force save
        self.browser.assert_no_element(f'input[name="rename[{old}]"]', wait=True)

    def test_lesson(self):
        b = self.browser
        b.visit("/lessons/")
        b.click_whatever("h2", text="II. Clean dirty data", wait=True)
        b.assert_element(
            ".title-metadata-stack", text="II. Clean dirty data", wait=True
        )

        self.import_module("dropna")
        self.import_module("nulldropper")
        self.import_module("reshape")
        self.import_module("converttodate")

        # 1. Introduction
        self.expect_highlight_next()
        self.click_next()

        # 2. Drop empty rows and columns
        self.expect_highlight(0, "a[name=loadurl]")
        self.add_data_step("Add from URL")

        # Wait for module to load
        self.expect_highlight(
            1, '.wf-module[data-module-name="Add from URL"]', wait=True
        )
        b.fill_in("url", DataUrl, wait=True)  # wait for module to load
        b.click_button("Update")

        # Wait for module to update
        self.expect_highlight(
            2, ".in-between-modules:last-child button.search", wait=True
        )
        self.add_wf_module("Drop empty columns")

        # Wait for module to load
        self.expect_highlight(
            3, ".in-between-modules:last-child button.search", wait=True
        )
        self.add_wf_module("Drop empty rows")

        # Wait for module to load
        self.expect_highlight(
            4, '.wf-module[data-module-name="Drop empty rows"]', wait=True
        )

        # Wait for column selector to load
        b.click_whatever(".react-select__indicator", wait=True)
        b.click_whatever(".react-select__option", text="MetroArea", wait=True)
        b.click_whatever(".react-select__indicator", wait=True)
        b.click_whatever(".react-select__option", text="Population", wait=True)
        self.submit_wf_module()

        self.expect_highlight_next()
        self.click_next()

        # 3. Convert types
        self.expect_highlight(0, ".in-between-modules:last-child button.search")
        self.add_wf_module("Convert to date & time")
        self.select_column("Convert to date & time", "colnames", "Date")
        self.submit_wf_module()

        self.expect_highlight(
            1,
            ".in-between-modules:last-child button.search",
            wait=True,  # wait for last exec to happen?
        )
        self.add_wf_module("Convert to numbers")
        self.select_column("Convert to numbers", "colnames", "Population")
        self.submit_wf_module()

        self.expect_highlight_next()
        self.click_next()

        # 4. Standardize column values
        self.expect_highlight(0, ".in-between-modules:last-child button.search")
        self.add_wf_module("Refine")

        # Wait for module to load
        self.expect_highlight(1, '.wf-module[data-module-name="Refine"]', wait=True)

        # Wait for column to appear
        self.select_column("Refine", "column", "MetroArea")

        # Wait for module to update
        self.expect_highlight(
            1,  # still not done this step
            '.wf-module[data-module-name="Refine"]',
            wait=True,
        )

        b.assert_element('input[name="rename[Seattle - Tacoma]"]', wait=True)
        self._rename_column("Austin", "Austin - Round Rock")
        self.expect_highlight(1)  # not done this step
        self._rename_column("DallasFORTHWorth", "Dallas - Fort Worth")
        self.submit_wf_module()

        self.expect_highlight_next()
        self.click_next()

        # 3. Changing table format
        self.expect_highlight(0, ".in-between-modules:last-child button.search")
        self.add_wf_module("Reshape")

        # Wait for module to start loading
        self.expect_highlight(1, '.wf-module[data-module-name="Reshape"]', wait=True)
        # Wait for module to load
        b.select("direction", "Long to wide", wait=True)
        self.submit_wf_module()

        # Wait for param change to register
        self.expect_highlight(2, '.wf-module[data-module-name="Reshape"]', wait=True)
        self.select_column("Reshape", "colnames", "Date")
        self.submit_wf_module()

        # Wait for param change to register
        self.expect_highlight(3, '.wf-module[data-module-name="Reshape"]', wait=True)
        self.select_column("Reshape", "varcol", "MetroArea")
        self.submit_wf_module()

        # Navigate to footer
        self.expect_highlight_next(wait=True)
        self.click_next()
        b.assert_no_element(".lesson-highlight")
