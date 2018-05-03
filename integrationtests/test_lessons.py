from integrationtests.utils import LoggedInIntegrationTest

class TestLessons(LoggedInIntegrationTest):
    def test_lesson_list(self):
        b = self.browser
        b.visit(self.live_server_url + '/lessons/')
        self.assertTrue(b.is_text_present('Load Public Data and Make a Chart'))

    def test_lesson_detail(self):
        b = self.browser
        b.visit(self.live_server_url + '/lessons/')
        b.find_by_xpath('//button[text()="Begin"]').click()

        self.assertTrue(b.url.endswith('/lessons/load-public-data/'))
        self.assertTrue(b.is_text_present('DROP MODULE HERE'))
        self.assertTrue(b.is_text_present('0. Introduction'))
        self.assertFalse(b.is_text_present('Duplicate'))
        self.assertFalse(b.is_text_present('Share'))
        self.assertFalse(b.is_text_present('1. Load Public Data by URL'))
