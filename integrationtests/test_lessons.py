from integrationtests.helpers import accounts
from integrationtests.utils import WorkbenchBase


class TestLessons(WorkbenchBase):
    def test_lesson_list_logged_in(self):
        self.user = self.account_admin.create_user("user@example.org")
        accounts.login(self.browser, self.user.email, self.user.email)

        b = self.browser
        b.visit("/lessons/")
        b.assert_element("h2", text="I. Load public data and make a chart", wait=True)

    def test_lesson_detail_logged_in(self):
        self.user = self.account_admin.create_user("user@example.org")
        accounts.login(self.browser, self.user.email, self.user.email)

        b = self.browser
        b.visit("/lessons/")
        b.click_whatever("h2", text="I. Load public data and make a chart", wait=True)

        b.assert_element(".module-stack")
        b.assert_element("h2", text="Overview")
        b.assert_element(".current-and-total", text="1 of 4")
        b.click_button("Next")
        b.assert_element("h2", text="Load Public Data by URL")

    def test_lesson_not_logged_in(self):
        # Lessons should work even when the user is not logged in
        # https://www.pivotaltracker.com/story/show/159674634
        b = self.browser
        b.visit("/lessons/")
        b.click_whatever("h2", text="I. Load public data and make a chart", wait=True)

        b.assert_element(".module-stack")
        b.assert_element("h2", text="Overview")
        b.assert_element(".current-and-total", text="1 of 4")
        b.click_button("Next")
        b.assert_element("h2", text="Load Public Data by URL")
