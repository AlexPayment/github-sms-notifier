import unittest

from github_sms_notifier import github_sms_notifier
import os


class GitHubSmsNotifierTest(unittest.TestCase):
    def setUp(self):
        with open(github_sms_notifier.SETTINGS_JSON_FILE_NAME, 'w+') as settings_file:
            settings_file.write(b'{"twilioAccountSid":"twilioAccountSid","twilioAuthToken":"twilioAuthToken","prOpened":true,"repositories":"full_name"}')
        github_sms_notifier.app.testing = True
        self.app = github_sms_notifier.app.test_client()

    def tearDown(self):
        os.remove(github_sms_notifier.SETTINGS_JSON_FILE_NAME)
        pass

    def test_get_admin(self):
        rv = self.app.get('/admin')
        assert 200 == rv.status_code
        assert rv.data

    def test_post_pull_requests(self):
        rv = self.app.post('/pullRequests', data='{"action":"opened","number":1,"pull_request":{"html_url":"https://github.com/AlexPayment"},"repository":{"full_name":"full_name"}}')
        assert 204 == rv.status_code

    def test_root(self):
        rv = self.app.get('/')
        assert 200 == rv.status_code


if __name__ == '__main__':
    unittest.main()