from integrationtests.utils import LoggedInIntegrationTest

class TestLessons(LoggedInIntegrationTest):
    def test_lesson_list(self):
        b = self.browser
        b.visit('/lessons/')
        b.assert_element(
            'h2',
            text='I. Load public data and make a chart',
            wait=True
        )

    def test_lesson_detail(self):
        b = self.browser
        b.visit('/lessons/')
        b.click_whatever('h2', text='I. Load public data and make a chart', wait=True)

        b.assert_element('.modulestack-empty', text='DROP MODULE HERE')
        b.assert_element('h2', text='Overview')
        b.assert_element('.current-and-total', text='1 of 4')
        b.click_button('Next')
        b.assert_element('h2', text='1. Load Public Data by URL')
