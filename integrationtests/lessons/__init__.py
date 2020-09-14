from integrationtests.utils import LoggedInIntegrationTest


class LessonTest(LoggedInIntegrationTest):
    def expect_highlight_next(self, **kwargs) -> None:
        """Assert highlight on the "Next" button at the lesson's footer.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        self.browser.assert_element("button[name=Next].lesson-highlight", **kwargs)

    def click_next(self) -> None:
        self.browser.click_button("Next")

    def expect_highlight(self, step_index: int, *selector, **kwargs) -> None:
        """Tests the right highlights are set in the DOM.

        We check:
        * ol.steps>li:nth-child(step_index+1) is .active
        * the given selector is .lesson-highlight

        Keyword arguments are passed to the selector, except:
        wait -- will be set when asserting elements for both checks.
        """
        step_kwargs = {}
        if "wait" in kwargs:
            step_kwargs["wait"] = kwargs["wait"]
        self.browser.assert_element(
            f"article.lesson ol.steps>li:nth-child({step_index+1}).active",
            **step_kwargs,
        )
        if selector:
            self.browser.assert_element(
                *selector,
                **kwargs,
                filter=lambda node: " lesson-highlight " in f' {node["class"]} ',
            )

    def assert_lesson_finished(self):
        """Returns if the lesson is finished."""
        self.browser.assert_no_element(".lesson-highlight")
