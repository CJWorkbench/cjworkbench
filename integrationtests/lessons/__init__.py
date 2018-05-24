from integrationtests.helpers.modules import import_workbench_module
from integrationtests.utils import LoggedInIntegrationTest

class LessonTest(LoggedInIntegrationTest):
    def import_module(self, slug: str) -> None:
        import_workbench_module(self.browser, 'columnchart')

    def expect_highlight_next(self) -> None:
        self.browser.assert_element('button[name=Next].lesson-highlight')

    def click_next(self) -> None:
        self.browser.click_button('Next')

    def expect_highlight(self, step_index: int, *selector, **kwargs) -> None:
        self.browser.assert_element(f'article.lesson ol.steps>li:nth-child({step_index+1}).active')
        self.browser.assert_element(
            *selector,
            **kwargs,
            filter=lambda node: ' lesson-highlight ' in f' {node["class"]} '
        )
