from server.tests.utils import *
from django.test import override_settings
from server.modules.twitter import *
import tempfile
import mock
from unittest.mock import patch
import json

# test data, excerpted from tweepy repo

user_timeline_json = "[{\"created_at\":\"Sat Nov 05 21:44:24 +0000 2016\",\"id\":795018956507582465,\"id_str\":\"795018956507582465\",\"full_text\":\"testing 1000 https:\\/\\/t.co\\/HFZNy7Fz9o\",\"truncated\":false,\"entities\":{\"hashtags\":[],\"symbols\":[],\"user_mentions\":[],\"urls\":[],\"media\":[{\"id\":795018953181593600,\"id_str\":\"795018953181593600\",\"indices\":[13,36],\"media_url\":\"http:\\/\\/pbs.twimg.com\\/media\\/Cwh5hpYXgAAXF-1.jpg\",\"media_url_https\":\"https:\\/\\/pbs.twimg.com\\/media\\/Cwh5hpYXgAAXF-1.jpg\",\"url\":\"https:\\/\\/t.co\\/HFZNy7Fz9o\",\"display_url\":\"pic.twitter.com\\/HFZNy7Fz9o\",\"expanded_url\":\"https:\\/\\/twitter.com\\/TheTweepyTester\\/status\\/795018956507582465\\/photo\\/1\",\"type\":\"photo\",\"sizes\":{\"small\":{\"w\":680,\"h\":340,\"resize\":\"fit\"},\"medium\":{\"w\":1200,\"h\":600,\"resize\":\"fit\"},\"thumb\":{\"w\":150,\"h\":150,\"resize\":\"crop\"},\"large\":{\"w\":1252,\"h\":626,\"resize\":\"fit\"}}}]},\"extended_entities\":{\"media\":[{\"id\":795018953181593600,\"id_str\":\"795018953181593600\",\"indices\":[13,36],\"media_url\":\"http:\\/\\/pbs.twimg.com\\/media\\/Cwh5hpYXgAAXF-1.jpg\",\"media_url_https\":\"https:\\/\\/pbs.twimg.com\\/media\\/Cwh5hpYXgAAXF-1.jpg\",\"url\":\"https:\\/\\/t.co\\/HFZNy7Fz9o\",\"display_url\":\"pic.twitter.com\\/HFZNy7Fz9o\",\"expanded_url\":\"https:\\/\\/twitter.com\\/TheTweepyTester\\/status\\/795018956507582465\\/photo\\/1\",\"type\":\"photo\",\"sizes\":{\"small\":{\"w\":680,\"h\":340,\"resize\":\"fit\"},\"medium\":{\"w\":1200,\"h\":600,\"resize\":\"fit\"},\"thumb\":{\"w\":150,\"h\":150,\"resize\":\"crop\"},\"large\":{\"w\":1252,\"h\":626,\"resize\":\"fit\"}}}]},\"source\":\"\\u003ca href=\\\"https:\\/\\/github.com\\/tweepy\\/tweepy\\\" rel=\\\"nofollow\\\"\\u003eTweepy dev\\u003c\\/a\\u003e\",\"in_reply_to_status_id\":null,\"in_reply_to_status_id_str\":null,\"in_reply_to_user_id\":null,\"in_reply_to_user_id_str\":null,\"in_reply_to_screen_name\":null,\"user\":{\"id\":794682839556038656,\"id_str\":\"794682839556038656\",\"name\":\"Tweepy Test\",\"screen_name\":\"TheTweepyTester\",\"location\":\"\",\"description\":\"\",\"url\":null,\"entities\":{\"description\":{\"urls\":[]}},\"protected\":false,\"followers_count\":1,\"friends_count\":18,\"listed_count\":0,\"created_at\":\"Fri Nov 04 23:28:48 +0000 2016\",\"favourites_count\":0,\"utc_offset\":-25200,\"time_zone\":\"Pacific Time (US & Canada)\",\"geo_enabled\":false,\"verified\":false,\"statuses_count\":112,\"lang\":\"en\",\"contributors_enabled\":false,\"is_translator\":false,\"is_translation_enabled\":false,\"profile_background_color\":\"000000\",\"profile_background_image_url\":\"http:\\/\\/abs.twimg.com\\/images\\/themes\\/theme1\\/bg.png\",\"profile_background_image_url_https\":\"https:\\/\\/abs.twimg.com\\/images\\/themes\\/theme1\\/bg.png\",\"profile_background_tile\":false,\"profile_image_url\":\"http:\\/\\/abs.twimg.com\\/sticky\\/default_profile_images\\/default_profile_6_normal.png\",\"profile_image_url_https\":\"https:\\/\\/abs.twimg.com\\/sticky\\/default_profile_images\\/default_profile_6_normal.png\",\"profile_banner_url\":\"https:\\/\\/pbs.twimg.com\\/profile_banners\\/794682839556038656\\/1478382257\",\"profile_link_color\":\"1B95E0\",\"profile_sidebar_border_color\":\"000000\",\"profile_sidebar_fill_color\":\"000000\",\"profile_text_color\":\"000000\",\"profile_use_background_image\":false,\"has_extended_profile\":false,\"default_profile\":false,\"default_profile_image\":true,\"following\":false,\"follow_request_sent\":false,\"notifications\":false,\"translator_type\":\"none\"},\"geo\":null,\"coordinates\":null,\"place\":null,\"contributors\":null,\"is_quote_status\":false,\"retweet_count\":0,\"favorite_count\":0,\"favorited\":false,\"retweeted\":false,\"possibly_sensitive\":false,\"lang\":\"en\"},{\"created_at\":\"Sat Nov 05 21:38:46 +0000 2016\",\"id\":795017539831103489,\"id_str\":\"795017539831103489\",\"full_text\":\"Hello\",\"truncated\":false,\"entities\":{\"hashtags\":[],\"symbols\":[],\"user_mentions\":[],\"urls\":[]},\"source\":\"\\u003ca href=\\\"http:\\/\\/twitter.com\\\" rel=\\\"nofollow\\\"\\u003eTwitter Web Client\\u003c\\/a\\u003e\",\"in_reply_to_status_id\":null,\"in_reply_to_status_id_str\":null,\"in_reply_to_user_id\":null,\"in_reply_to_user_id_str\":null,\"in_reply_to_screen_name\":null,\"user\":{\"id\":794682839556038656,\"id_str\":\"794682839556038656\",\"name\":\"Tweepy Test\",\"screen_name\":\"TheTweepyTester\",\"location\":\"\",\"description\":\"\",\"url\":null,\"entities\":{\"description\":{\"urls\":[]}},\"protected\":false,\"followers_count\":1,\"friends_count\":18,\"listed_count\":0,\"created_at\":\"Fri Nov 04 23:28:48 +0000 2016\",\"favourites_count\":0,\"utc_offset\":-25200,\"time_zone\":\"Pacific Time (US & Canada)\",\"geo_enabled\":false,\"verified\":false,\"statuses_count\":112,\"lang\":\"en\",\"contributors_enabled\":false,\"is_translator\":false,\"is_translation_enabled\":false,\"profile_background_color\":\"000000\",\"profile_background_image_url\":\"http:\\/\\/abs.twimg.com\\/images\\/themes\\/theme1\\/bg.png\",\"profile_background_image_url_https\":\"https:\\/\\/abs.twimg.com\\/images\\/themes\\/theme1\\/bg.png\",\"profile_background_tile\":false,\"profile_image_url\":\"http:\\/\\/abs.twimg.com\\/sticky\\/default_profile_images\\/default_profile_6_normal.png\",\"profile_image_url_https\":\"https:\\/\\/abs.twimg.com\\/sticky\\/default_profile_images\\/default_profile_6_normal.png\",\"profile_banner_url\":\"https:\\/\\/pbs.twimg.com\\/profile_banners\\/794682839556038656\\/1478382257\",\"profile_link_color\":\"1B95E0\",\"profile_sidebar_border_color\":\"000000\",\"profile_sidebar_fill_color\":\"000000\",\"profile_text_color\":\"000000\",\"profile_use_background_image\":false,\"has_extended_profile\":false,\"default_profile\":false,\"default_profile_image\":true,\"following\":false,\"follow_request_sent\":false,\"notifications\":false,\"translator_type\":\"none\"},\"geo\":null,\"coordinates\":null,\"place\":null,\"contributors\":null,\"is_quote_status\":false,\"retweet_count\":0,\"favorite_count\":0,\"favorited\":false,\"retweeted\":false,\"lang\":\"en\"}]"


# test data, from tweepy repo
user_timeline2_json = "[{\"created_at\":\"Sat Nov 05 21:38:46 +0000 2016\",\"id\":795017539831103489,\"id_str\":\"795017539831103489\",\"full_text\":\"Hello\",\"truncated\":false,\"entities\":{\"hashtags\":[],\"symbols\":[],\"user_mentions\":[],\"urls\":[]},\"source\":\"\\u003ca href=\\\"http:\\/\\/twitter.com\\\" rel=\\\"nofollow\\\"\\u003eTwitter Web Client\\u003c\\/a\\u003e\",\"in_reply_to_status_id\":null,\"in_reply_to_status_id_str\":null,\"in_reply_to_user_id\":null,\"in_reply_to_user_id_str\":null,\"in_reply_to_screen_name\":null,\"user\":{\"id\":794682839556038656,\"id_str\":\"794682839556038656\",\"name\":\"Tweepy Test\",\"screen_name\":\"TheTweepyTester\",\"location\":\"\",\"description\":\"\",\"url\":null,\"entities\":{\"description\":{\"urls\":[]}},\"protected\":false,\"followers_count\":1,\"friends_count\":18,\"listed_count\":0,\"created_at\":\"Fri Nov 04 23:28:48 +0000 2016\",\"favourites_count\":0,\"utc_offset\":-25200,\"time_zone\":\"Pacific Time (US & Canada)\",\"geo_enabled\":false,\"verified\":false,\"statuses_count\":112,\"lang\":\"en\",\"contributors_enabled\":false,\"is_translator\":false,\"is_translation_enabled\":false,\"profile_background_color\":\"000000\",\"profile_background_image_url\":\"http:\\/\\/abs.twimg.com\\/images\\/themes\\/theme1\\/bg.png\",\"profile_background_image_url_https\":\"https:\\/\\/abs.twimg.com\\/images\\/themes\\/theme1\\/bg.png\",\"profile_background_tile\":false,\"profile_image_url\":\"http:\\/\\/abs.twimg.com\\/sticky\\/default_profile_images\\/default_profile_6_normal.png\",\"profile_image_url_https\":\"https:\\/\\/abs.twimg.com\\/sticky\\/default_profile_images\\/default_profile_6_normal.png\",\"profile_banner_url\":\"https:\\/\\/pbs.twimg.com\\/profile_banners\\/794682839556038656\\/1478382257\",\"profile_link_color\":\"1B95E0\",\"profile_sidebar_border_color\":\"000000\",\"profile_sidebar_fill_color\":\"000000\",\"profile_text_color\":\"000000\",\"profile_use_background_image\":false,\"has_extended_profile\":false,\"default_profile\":false,\"default_profile_image\":true,\"following\":false,\"follow_request_sent\":false,\"notifications\":false,\"translator_type\":\"none\"},\"geo\":null,\"coordinates\":null,\"place\":null,\"contributors\":null,\"is_quote_status\":false,\"retweet_count\":0,\"favorite_count\":0,\"favorited\":false,\"retweeted\":false,\"lang\":\"en\"},{\"created_at\":\"Sat Nov 05 21:37:13 +0000 2016\",\"id\":795017147651162112,\"id_str\":\"795017147651162112\",\"full_text\":\"testing 1000 https:\\/\\/t.co\\/3vt8ITRQ3w\",\"truncated\":false,\"entities\":{\"hashtags\":[],\"symbols\":[],\"user_mentions\":[],\"urls\":[],\"media\":[{\"id\":795017144849272832,\"id_str\":\"795017144849272832\",\"indices\":[13,36],\"media_url\":\"http:\\/\\/pbs.twimg.com\\/media\\/Cwh34Y0WEAA6m1l.jpg\",\"media_url_https\":\"https:\\/\\/pbs.twimg.com\\/media\\/Cwh34Y0WEAA6m1l.jpg\",\"url\":\"https:\\/\\/t.co\\/3vt8ITRQ3w\",\"display_url\":\"pic.twitter.com\\/3vt8ITRQ3w\",\"expanded_url\":\"https:\\/\\/twitter.com\\/TheTweepyTester\\/status\\/795017147651162112\\/photo\\/1\",\"type\":\"photo\",\"sizes\":{\"medium\":{\"w\":1200,\"h\":600,\"resize\":\"fit\"},\"large\":{\"w\":1252,\"h\":626,\"resize\":\"fit\"},\"thumb\":{\"w\":150,\"h\":150,\"resize\":\"crop\"},\"small\":{\"w\":680,\"h\":340,\"resize\":\"fit\"}}}]},\"extended_entities\":{\"media\":[{\"id\":795017144849272832,\"id_str\":\"795017144849272832\",\"indices\":[13,36],\"media_url\":\"http:\\/\\/pbs.twimg.com\\/media\\/Cwh34Y0WEAA6m1l.jpg\",\"media_url_https\":\"https:\\/\\/pbs.twimg.com\\/media\\/Cwh34Y0WEAA6m1l.jpg\",\"url\":\"https:\\/\\/t.co\\/3vt8ITRQ3w\",\"display_url\":\"pic.twitter.com\\/3vt8ITRQ3w\",\"expanded_url\":\"https:\\/\\/twitter.com\\/TheTweepyTester\\/status\\/795017147651162112\\/photo\\/1\",\"type\":\"photo\",\"sizes\":{\"medium\":{\"w\":1200,\"h\":600,\"resize\":\"fit\"},\"large\":{\"w\":1252,\"h\":626,\"resize\":\"fit\"},\"thumb\":{\"w\":150,\"h\":150,\"resize\":\"crop\"},\"small\":{\"w\":680,\"h\":340,\"resize\":\"fit\"}}}]},\"source\":\"\\u003ca href=\\\"https:\\/\\/github.com\\/tweepy\\/tweepy\\\" rel=\\\"nofollow\\\"\\u003eTweepy dev\\u003c\\/a\\u003e\",\"in_reply_to_status_id\":null,\"in_reply_to_status_id_str\":null,\"in_reply_to_user_id\":null,\"in_reply_to_user_id_str\":null,\"in_reply_to_screen_name\":null,\"user\":{\"id\":794682839556038656,\"id_str\":\"794682839556038656\",\"name\":\"Tweepy Test\",\"screen_name\":\"TheTweepyTester\",\"location\":\"\",\"description\":\"\",\"url\":null,\"entities\":{\"description\":{\"urls\":[]}},\"protected\":false,\"followers_count\":1,\"friends_count\":18,\"listed_count\":0,\"created_at\":\"Fri Nov 04 23:28:48 +0000 2016\",\"favourites_count\":0,\"utc_offset\":-25200,\"time_zone\":\"Pacific Time (US & Canada)\",\"geo_enabled\":false,\"verified\":false,\"statuses_count\":112,\"lang\":\"en\",\"contributors_enabled\":false,\"is_translator\":false,\"is_translation_enabled\":false,\"profile_background_color\":\"000000\",\"profile_background_image_url\":\"http:\\/\\/abs.twimg.com\\/images\\/themes\\/theme1\\/bg.png\",\"profile_background_image_url_https\":\"https:\\/\\/abs.twimg.com\\/images\\/themes\\/theme1\\/bg.png\",\"profile_background_tile\":false,\"profile_image_url\":\"http:\\/\\/abs.twimg.com\\/sticky\\/default_profile_images\\/default_profile_6_normal.png\",\"profile_image_url_https\":\"https:\\/\\/abs.twimg.com\\/sticky\\/default_profile_images\\/default_profile_6_normal.png\",\"profile_banner_url\":\"https:\\/\\/pbs.twimg.com\\/profile_banners\\/794682839556038656\\/1478382257\",\"profile_link_color\":\"1B95E0\",\"profile_sidebar_border_color\":\"000000\",\"profile_sidebar_fill_color\":\"000000\",\"profile_text_color\":\"000000\",\"profile_use_background_image\":false,\"has_extended_profile\":false,\"default_profile\":false,\"default_profile_image\":true,\"following\":false,\"follow_request_sent\":false,\"notifications\":false,\"translator_type\":\"none\"},\"geo\":null,\"coordinates\":null,\"place\":null,\"contributors\":null,\"is_quote_status\":false,\"retweet_count\":0,\"favorite_count\":0,\"favorited\":false,\"retweeted\":false,\"possibly_sensitive\":false,\"lang\":\"en\"}]"


# make some fake tweet objects for our module to process, in tweepy Status object compatible format
def make_mock_statuses(json_text):
    class Status(object):
        pass

    tweet_array = json.loads(json_text)
    statuses = []

    for t in tweet_array:
        status = Status()
        for key in t:
            setattr(status, key, t[key])
        statuses.append(status)

    return statuses

# Turn those status objects into a Pandas table
def make_mock_tweet_table(statuses):
    cols = ['id', 'created_at', 'full_text', 'in_reply_to_screen_name', 'in_reply_to_status_id', 'retweeted',
            'retweet_count', 'favorited', 'favorite_count', 'source']

    tweets = [[getattr(t, x) for x in cols] for t in statuses]
    table = pd.DataFrame(tweets, columns=cols)
    table.rename(columns={'full_text': 'text'}, inplace=True)  # 280 chars should still be called 'text', meh
    return table


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class TwitterTests(LoggedInTestCase):

    def setUp(self):
        super(TwitterTests, self).setUp()  # log in
        self.wf_module = load_and_add_module('twitter')
        self.query_pval = get_param_by_id_name('query')
        self.username_pval = get_param_by_id_name('username')
        self.type_pval = get_param_by_id_name('querytype')

        self.env_patch = { 'CJW_TWITTER_CONSUMER_KEY':'mykey',
                           'CJW_TWITTER_CONSUMER_SECRET' : 'mysecret' }

        self.mock_statuses = make_mock_statuses(user_timeline_json)
        self.mock_tweet_table = make_mock_tweet_table(self.mock_statuses)
        self.mock_statuses2 = make_mock_statuses(user_timeline2_json)
        self.mock_tweet_table2 = make_mock_tweet_table(self.mock_statuses2)

    # send fetch event to button to load data. Type=click forces version to update, which tests expect
    def press_fetch_button(self):
        Twitter.event(self.wf_module,  {'type': 'click'})

    def test_empty_query(self):
        self.query_pval.set_value('')
        self.query_pval.save()
        self.press_fetch_button()
        self.assertEqual(self.wf_module.status, WfModule.ERROR)

    def test_user_timeline(self):
        self.username_pval.set_value('foouser')
        self.username_pval.save()
        self.type_pval.set_value(0)  # user timeline, as opposed to search
        self.type_pval.save()

        # should be no data saved yet, no Deltas on the workflow
        self.assertIsNone(self.wf_module.get_fetched_data_version())
        self.assertIsNone(self.wf_module.retrieve_fetched_table())
        self.assertIsNone(self.wf_module.workflow.last_delta)

        with patch.dict('os.environ', self.env_patch):
            with mock.patch('tweepy.AppAuthHandler') as auth:
                with mock.patch('tweepy.API') as api:
                    instance = api.return_value

                    # Actually fetch!
                    instance.user_timeline.return_value = self.mock_statuses
                    self.press_fetch_button()
                    self.assertEqual(self.wf_module.status, WfModule.READY)

                    # should create a new data version on the WfModule, and a new delta representing the change
                    self.wf_module.refresh_from_db()
                    self.wf_module.workflow.refresh_from_db()
                    first_version = self.wf_module.get_fetched_data_version()
                    first_delta = self.wf_module.workflow.last_delta
                    self.assertIsNotNone(first_version)
                    self.assertIsNotNone(first_delta)

                    # Check that render output is right
                    table = Twitter.render(self.wf_module, None)
                    self.assertTrue(table.equals(self.mock_tweet_table))
                    self.assertEqual(len(table), 2)

                    # now accumulate new tweets
                    instance.user_timeline.return_value = self.mock_statuses2
                    self.press_fetch_button()
                    self.assertEqual(self.wf_module.status, WfModule.READY)

                    # output should be only new tweets (in this case, one new tweet) appended to old tweets
                    table2 = Twitter.render(self.wf_module, None)
                    merged_table = pd.concat([ self.mock_tweet_table, self.mock_tweet_table2.iloc[[1]] ],ignore_index=True)
                    self.assertTrue(table2.equals(merged_table))
                    self.assertEqual(len(table2), 3)
