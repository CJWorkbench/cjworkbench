from integrationtests.helpers.modules import import_workbench_module
from integrationtests.utils import LoggedInIntegrationTest

class LessonTest(LoggedInIntegrationTest):
    def import_module(self, slug: str) -> None:
        import_workbench_module(self.browser, slug)


    def expect_highlight_next(self, **kwargs) -> None:
        """Assert highlight on the "Next" button at the lesson's footer.
        
        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self.browser.assert_element(
            'button[name=Next].lesson-highlight',
            **kwargs
        )


    def click_next(self) -> None:
        self.browser.click_button('Next')


    def expect_highlight(self, step_index: int, *selector, **kwargs) -> None:
        """Tests the right highlights are set in the DOM.
        
        We check:
        * ol.steps>li:nth-child(step_index+1) is .active
        * the given selector is .lesson-highlight

        Keyword arguments are passed to the selector, except:
        wait -- will be set when asserting elements for both checks.
        """
        step_kwargs = {}
        if 'wait' in kwargs: step_kwargs['wait'] = kwargs['wait']
        self.browser.assert_element(
            f'article.lesson ol.steps>li:nth-child({step_index+1}).active',
            **step_kwargs
        )
        if selector:
            self.browser.assert_element(
                *selector,
                **kwargs,
                filter=lambda node: ' lesson-highlight ' in f' {node["class"]} '
            )


    def assert_lesson_finished(self):
        """Returns if the lesson is finished.
        """
        self.browser.assert_no_element('.lesson-highlight')

    def select_column(self, name: str, text: str, **kwargs) -> None:
        """Selects 'text' in the ColumnSelect box with name 'name'.

        Waits for '.loading' to disappear before filling in the text.

        Note: unlike browser.select(), this does _not_ handle id or
        label locators.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self.browser.assert_element(
            f'select[name="{name}"]:not(.loading)',
            wait=True
        )
        self.browser.select(name, text, **kwargs)

    def add_wf_module(self, name: str, position=None) -> None:
        """Adds module with name 'name' to the workflow.

        Keyword arguments:
        position -- if set, add after the 'position'th existing module.
        """
        b = self.browser

        if position is None:
            with b.scope('.in-between-modules:last-child'):
                b.click_button('Add Module')
        else:
            i = position * 2 + 1
            with b.scope(f'.in-between-modules:nth-child({i})'):
                b.click_button('Add Module')

        # Search. That way, we won't need to worry about overflow:auto
        b.fill_in('moduleQ', name)

        b.click_whatever('li.module-search-result', text=name)

        b.assert_element(f'.wf-module[data-module-name="{name}"]', wait=True)
