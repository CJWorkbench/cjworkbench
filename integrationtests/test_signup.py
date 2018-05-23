from integrationtests.utils import WorkbenchBase
import re


class TestSignup(WorkbenchBase):
    def test_signup(self):
        url_regex = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+confirm-email(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

        b = self.browser
        # This will break when signup is open to the public
        b.visit(self.live_server_url + '/xyzzy/signup/')

        #self.assertTrue(b.is_element_present_by_text('Use Facebook account'))
        #self.assertTrue(b.is_element_present_by_text('Use Google account'))

        b.fill_in('email', 'user@example.org')
        b.fill_in('first_name', 'Jane')
        b.fill_in('last_name', 'Doe')
        b.fill_in('password1', '?P455W0rd!')
        b.fill_in('password2', '?P455W0rd!')
        b.click_button('Register')

        b.assert_element('h1', text='Verify Your E-mail Address', wait=True)

        # Test the email is right
        email = self.account_admin.latest_sent_email
        self.assertTrue(email)
        self.assertEqual('user@example.org', email['To'])
        body = email.get_payload()
        url = url_regex.search(body)
        self.assertTrue(url and url.group(0))

        # Follow the link
        b.visit(url.group(0))
        b.click_button('Confirm', wait=True)

        # Now log in with our new account
        # TODO _why_? The user already logged in
        b.fill_in('login', 'user@example.org', wait=True)
        b.fill_in('password', '?P455W0rd!')
        b.click_button('Sign In')
        b.wait_for_element('h3', text='WORKFLOWS', wait=True)
