from integrationtests.utils import LoggedInIntegrationTest

class TestLessons(LoggedInIntegrationTest):
    def test_lesson_list(self):
        b = self.browser
        b.visit(self.live_server_url + '/lessons/')
        import time; time.sleep(5)
        self.assertTrue(b.is_text_present('Load public data and make a column chart'))

    def test_lesson_detail(self):
        b = self.browser
        b.visit(self.live_server_url + '/lessons/')
        b.find_by_xpath('//h2[contains(text(),"Load public data")]').click()



        self.assertTrue(b.url.endswith('/lessons/load-public-data/'))
        self.assertTrue(b.is_text_present('DROP MODULE HERE'))
        self.assertTrue(b.is_text_present('Overview'))
        self.assertFalse(b.is_text_present('Duplicate'))
        self.assertFalse(b.is_text_present('Share'))
        self.assertFalse(b.is_text_present('1. Load Public Data by URL'))
