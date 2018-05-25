from integrationtests.helpers.modules import import_workbench_module
from integrationtests.utils import LoggedInIntegrationTest

class LessonTest(LoggedInIntegrationTest):
    def import_module(self, slug: str) -> None:
        import_workbench_module(self.browser, slug)


    def expect_highlight_next(self) -> None:
        self.browser.assert_element('button[name=Next].lesson-highlight')


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
        self.browser.assert_element(
            *selector,
            **kwargs,
            filter=lambda node: ' lesson-highlight ' in f' {node["class"]} '
        )


    def assert_lesson_finished(self):
        """Returns if the lesson is finished.
        """
        self.browser.assert_no_element('.lesson-highlight')


    def add_wf_module(self, name: str, position=None) -> None:
        """Adds module with name 'name' to the workflow.

        Keyword arguments:
        position -- if set, add after the 'position'th existing module.
        """
        # Search. That way, we won't need to worry about overflow:auto
        self.browser.fill_in('Modules', name)
        # wait for results to render. sleep() is the easiest way: mid-input,
        # a matching .module-search-result will exist, but it will later
        # be deleted/moved. So just waiting for it to exist isn't enough.
        import time; time.sleep(0.25)
        if position is None:
            self.browser.click_whatever(
                f'.module-search-result[data-module-name="{name}"]',
                wait=True
            )
        else:
            # react-dnd error https://github.com/react-dnd/react-dnd/issues/391 might be
            # our problem. Or it might be Firefox bug
            # https://bugzilla.mozilla.org/show_bug.cgi?id=1452131. Or maybe they're the
            # same bug? Drag-and-drop is HELL.
            #
            # TODO wait for one of the bugs to go away. Or change the design so we don't
            # _require_ drag-and-drop to make the lessons work.
            #
            # (There is an _actual_, reproducible Firefox bug: start dragging, then move
            # your mouse quickly and wildly. Expected results: you drag the thing around.
            # Actual results: the thing freezes.
            raise NotImplemented("TODO nix DnD: Selenium hates it")

        # Wait for module to load:
        # 1. see the element (which, in a race, may be a placeholder)
        # 2. wait to make sure the element isn't a placeholder
        # Assumes there's only one of a module in the lesson
        self.browser.assert_element(f'.wf-module[data-module-name="{name}"]',
                                    wait=True)
        self.browser.assert_no_element('.wf-module--placeholder', wait=True)
