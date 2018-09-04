import json
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from unittest.mock import patch
from tweepy.models import Status
from server.modules.twitter import Twitter
from server.modules.types import ProcessResult


def table_to_result(table):
    result = ProcessResult(table)
    result.sanitize_in_place()  # alters dataframe.equals() result
    return result


# test data, excerpted from tweepy repo.
# One overlapping tweet between the two sets of two tweets
# Added whitespace makes nvim syntax-highlight much more quickly.
user_timeline_json = """[
{
    "created_at":"Sat Nov 05 21:38:46 +0000 2016",
    "id":795017539831103489,
    "id_str":"795017539831103489",
    "full_text":"Hello",
    "truncated":false,
    "entities":{"hashtags":[],"symbols":[],"user_mentions":[],"urls":[]},
    "source":"\\u003ca href=\\"http://twitter.com\\" rel=\\"nofollow\\"\\u003eTwitter Web Client\\u003c/a\\u003e",
    "in_reply_to_status_id":null,
    "in_reply_to_status_id_str":null,
    "in_reply_to_user_id":null,
    "in_reply_to_user_id_str":null,
    "in_reply_to_screen_name":null,
    "user":{"id":794682839556038656,"id_str":"794682839556038656","name":"Tweepy Test","screen_name":"TheTweepyTester","location":"","description":"","url":null,"entities":{"description":{"urls":[]}},"protected":false,"followers_count":1,"friends_count":18,"listed_count":0,"created_at":"Fri Nov 04 23:28:48 +0000 2016","favourites_count":0,"utc_offset":-25200,"time_zone":"Pacific Time (US & Canada)","geo_enabled":false,"verified":false,"statuses_count":112,"lang":"en","contributors_enabled":false,"is_translator":false,"is_translation_enabled":false,"profile_background_color":"000000","profile_background_image_url":"http://abs.twimg.com/images/themes/theme1/bg.png","profile_background_image_url_https":"https://abs.twimg.com/images/themes/theme1/bg.png","profile_background_tile":false,"profile_image_url":"http://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png","profile_image_url_https":"https://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png","profile_banner_url":"https://pbs.twimg.com/profile_banners/794682839556038656/1478382257","profile_link_color":"1B95E0","profile_sidebar_border_color":"000000","profile_sidebar_fill_color":"000000","profile_text_color":"000000","profile_use_background_image":false,"has_extended_profile":false,"default_profile":false,"default_profile_image":true,"following":false,"follow_request_sent":false,"notifications":false,"translator_type":"none"},
    "geo":null,
    "coordinates":null,
    "place":null,
    "contributors":null,
    "is_quote_status":false,
    "retweet_count":0,
    "favorite_count":0,
    "favorited":false,
    "retweeted":false,
    "lang":"en"
},
{
    "created_at":"Sat Nov 05 21:37:13 +0000 2016",
    "id":795017147651162112,
    "id_str":"795017147651162112",
    "full_text":"testing 1000 https://t.co/3vt8ITRQ3w",
    "truncated":false,
    "entities":{"hashtags":[],"symbols":[],"user_mentions":[],"urls":[],"media":[{"id":795017144849272832,"id_str":"795017144849272832","indices":[13,36],"media_url":"http://pbs.twimg.com/media/Cwh34Y0WEAA6m1l.jpg","media_url_https":"https://pbs.twimg.com/media/Cwh34Y0WEAA6m1l.jpg","url":"https://t.co/3vt8ITRQ3w","display_url":"pic.twitter.com/3vt8ITRQ3w","expanded_url":"https://twitter.com/TheTweepyTester/status/795017147651162112/photo/1","type":"photo","sizes":{"medium":{"w":1200,"h":600,"resize":"fit"},"large":{"w":1252,"h":626,"resize":"fit"},"thumb":{"w":150,"h":150,"resize":"crop"},"small":{"w":680,"h":340,"resize":"fit"}}}]},
    "extended_entities":{"media":[{"id":795017144849272832,"id_str":"795017144849272832","indices":[13,36],"media_url":"http://pbs.twimg.com/media/Cwh34Y0WEAA6m1l.jpg","media_url_https":"https://pbs.twimg.com/media/Cwh34Y0WEAA6m1l.jpg","url":"https://t.co/3vt8ITRQ3w","display_url":"pic.twitter.com/3vt8ITRQ3w","expanded_url":"https://twitter.com/TheTweepyTester/status/795017147651162112/photo/1","type":"photo","sizes":{"medium":{"w":1200,"h":600,"resize":"fit"},"large":{"w":1252,"h":626,"resize":"fit"},"thumb":{"w":150,"h":150,"resize":"crop"},"small":{"w":680,"h":340,"resize":"fit"}}}]},
    "source":"\\u003ca href=\\"https://github.com/tweepy/tweepy\\" rel=\\"nofollow\\"\\u003eTweepy dev\\u003c/a\\u003e",
    "in_reply_to_status_id":null,
    "in_reply_to_status_id_str":null,
    "in_reply_to_user_id":null,
    "in_reply_to_user_id_str":null,
    "in_reply_to_screen_name":null,
    "user":{"id":794682839556038656,"id_str":"794682839556038656","name":"Tweepy Test","screen_name":"TheTweepyTester","location":"","description":"","url":null,"entities":{"description":{"urls":[]}},"protected":false,"followers_count":1,"friends_count":18,"listed_count":0,"created_at":"Fri Nov 04 23:28:48 +0000 2016","favourites_count":0,"utc_offset":-25200,"time_zone":"Pacific Time (US & Canada)","geo_enabled":false,"verified":false,"statuses_count":112,"lang":"en","contributors_enabled":false,"is_translator":false,"is_translation_enabled":false,"profile_background_color":"000000","profile_background_image_url":"http://abs.twimg.com/images/themes/theme1/bg.png","profile_background_image_url_https":"https://abs.twimg.com/images/themes/theme1/bg.png","profile_background_tile":false,"profile_image_url":"http://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png","profile_image_url_https":"https://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png","profile_banner_url":"https://pbs.twimg.com/profile_banners/794682839556038656/1478382257","profile_link_color":"1B95E0","profile_sidebar_border_color":"000000","profile_sidebar_fill_color":"000000","profile_text_color":"000000","profile_use_background_image":false,"has_extended_profile":false,"default_profile":false,"default_profile_image":true,"following":false,"follow_request_sent":false,"notifications":false,"translator_type":"none"},
    "geo":null,
    "coordinates":null,
    "place":null,
    "contributors":null,
    "is_quote_status":false,
    "retweet_count":0,
    "favorite_count":0,
    "favorited":false,
    "retweeted":false,
    "possibly_sensitive":false,
    "lang":"en"
}
]"""
user_timeline2_json = """[
{
    "created_at":"Sat Nov 05 21:44:24 +0000 2016",
    "id":795018956507582465,
    "id_str":"795018956507582465",
    "full_text":"testing 1000 https://t.co/HFZNy7Fz9o",
    "truncated":false,
    "entities":{"hashtags":[],"symbols":[],"user_mentions":[],"urls":[],"media":[{"id":795018953181593600,"id_str":"795018953181593600","indices":[13,36],"media_url":"http://pbs.twimg.com/media/Cwh5hpYXgAAXF-1.jpg","media_url_https":"https://pbs.twimg.com/media/Cwh5hpYXgAAXF-1.jpg","url":"https://t.co/HFZNy7Fz9o","display_url":"pic.twitter.com/HFZNy7Fz9o","expanded_url":"https://twitter.com/TheTweepyTester/status/795018956507582465/photo/1","type":"photo","sizes":{"small":{"w":680,"h":340,"resize":"fit"},"medium":{"w":1200,"h":600,"resize":"fit"},"thumb":{"w":150,"h":150,"resize":"crop"},"large":{"w":1252,"h":626,"resize":"fit"}}}]},
    "extended_entities":{"media":[{"id":795018953181593600,"id_str":"795018953181593600","indices":[13,36],"media_url":"http://pbs.twimg.com/media/Cwh5hpYXgAAXF-1.jpg","media_url_https":"https://pbs.twimg.com/media/Cwh5hpYXgAAXF-1.jpg","url":"https://t.co/HFZNy7Fz9o","display_url":"pic.twitter.com/HFZNy7Fz9o","expanded_url":"https://twitter.com/TheTweepyTester/status/795018956507582465/photo/1","type":"photo","sizes":{"small":{"w":680,"h":340,"resize":"fit"},"medium":{"w":1200,"h":600,"resize":"fit"},"thumb":{"w":150,"h":150,"resize":"crop"},"large":{"w":1252,"h":626,"resize":"fit"}}}]},
    "source":"\\u003ca href=\\"https://github.com/tweepy/tweepy\\" rel=\\"nofollow\\"\\u003eTweepy dev\\u003c/a\\u003e",
    "in_reply_to_status_id":null,
    "in_reply_to_status_id_str":null,
    "in_reply_to_user_id":null,
    "in_reply_to_user_id_str":null,
    "in_reply_to_screen_name":null,
    "user":{"id":794682839556038656,"id_str":"794682839556038656","name":"Tweepy Test","screen_name":"TheTweepyTester","location":"","description":"","url":null,"entities":{"description":{"urls":[]}},"protected":false,"followers_count":1,"friends_count":18,"listed_count":0,"created_at":"Fri Nov 04 23:28:48 +0000 2016","favourites_count":0,"utc_offset":-25200,"time_zone":"Pacific Time (US & Canada)","geo_enabled":false,"verified":false,"statuses_count":112,"lang":"en","contributors_enabled":false,"is_translator":false,"is_translation_enabled":false,"profile_background_color":"000000","profile_background_image_url":"http://abs.twimg.com/images/themes/theme1/bg.png","profile_background_image_url_https":"https://abs.twimg.com/images/themes/theme1/bg.png","profile_background_tile":false,"profile_image_url":"http://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png","profile_image_url_https":"https://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png","profile_banner_url":"https://pbs.twimg.com/profile_banners/794682839556038656/1478382257","profile_link_color":"1B95E0","profile_sidebar_border_color":"000000","profile_sidebar_fill_color":"000000","profile_text_color":"000000","profile_use_background_image":false,"has_extended_profile":false,"default_profile":false,"default_profile_image":true,"following":false,"follow_request_sent":false,"notifications":false,"translator_type":"none"},
    "geo":null,
    "coordinates":null,
    "place":null,
    "contributors":null,
    "is_quote_status":false,
    "retweet_count":0,
    "favorite_count":0,
    "favorited":false,
    "retweeted":false,
    "possibly_sensitive":false,
    "lang":"en"
},
{
    "created_at":"Sat Nov 05 21:38:46 +0000 2016",
    "id":795017539831103489,
    "id_str":"795017539831103489",
    "full_text":"Hello",
    "truncated":false,
    "entities":{"hashtags":[],"symbols":[],"user_mentions":[],"urls":[]},
    "source":"\\u003ca href=\\"http://twitter.com\\" rel=\\"nofollow\\"\\u003eTwitter Web Client\\u003c/a\\u003e",
    "in_reply_to_status_id":null,
    "in_reply_to_status_id_str":null,
    "in_reply_to_user_id":null,
    "in_reply_to_user_id_str":null,
    "in_reply_to_screen_name":null,
    "user":{"id":794682839556038656,"id_str":"794682839556038656","name":"Tweepy Test","screen_name":"TheTweepyTester","location":"","description":"","url":null,"entities":{"description":{"urls":[]}},"protected":false,"followers_count":1,"friends_count":18,"listed_count":0,"created_at":"Fri Nov 04 23:28:48 +0000 2016","favourites_count":0,"utc_offset":-25200,"time_zone":"Pacific Time (US & Canada)","geo_enabled":false,"verified":false,"statuses_count":112,"lang":"en","contributors_enabled":false,"is_translator":false,"is_translation_enabled":false,"profile_background_color":"000000","profile_background_image_url":"http://abs.twimg.com/images/themes/theme1/bg.png","profile_background_image_url_https":"https://abs.twimg.com/images/themes/theme1/bg.png","profile_background_tile":false,"profile_image_url":"http://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png","profile_image_url_https":"https://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png","profile_banner_url":"https://pbs.twimg.com/profile_banners/794682839556038656/1478382257","profile_link_color":"1B95E0","profile_sidebar_border_color":"000000","profile_sidebar_fill_color":"000000","profile_text_color":"000000","profile_use_background_image":false,"has_extended_profile":false,"default_profile":false,"default_profile_image":true,"following":false,"follow_request_sent":false,"notifications":false,"translator_type":"none"},
    "geo":null,
    "coordinates":null,
    "place":null,
    "contributors":null,
    "is_quote_status":false,
    "retweet_count":0,
    "favorite_count":0,
    "favorited":false,
    "retweeted":false,
    "lang":"en"
}
]"""


# make some fake tweet objects for our module to process, in tweepy Status
# object compatible format
def make_mock_statuses(json_text):
    tweet_array = json.loads(json_text)
    statuses = Status.parse_list(None, tweet_array)
    return statuses

# Turn those status objects into a Pandas table
def make_mock_tweet_table(statuses):
    cols = ['created_at', 'full_text', 'retweet_count', 'favorite_count', 'in_reply_to_screen_name', 'source', 'id']

    tweets = [[getattr(t, x) for x in cols] for t in statuses]
    table = pd.DataFrame(tweets, columns=cols)
    table.insert(0, 'screen_name', [t.user.screen_name for t in statuses])
    table.rename(columns={'full_text': 'text'}, inplace=True)  # 280 chars should still be called 'text', meh
    return table


class MockWfModule:
    def __init__(self, **kwargs):
        self.querytype = 0
        self.username = 'username'
        self.query = 'query'
        self.listurl = 'listurl'
        self.twitter_credentials = {
            'oauth_token': 'a-token',
            'oauth_token_secret': 'a-token-secret',
        }
        self.accumulate = True
        self.fetched_table = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_param_menu_idx(self, param):
        return getattr(self, param)

    def get_param_string(self, param):
        return getattr(self, param)

    def get_param_secret_secret(self, param):
        return getattr(self, param)

    def get_param_checkbox(self, param):
        return getattr(self, param)

    def retrieve_fetched_table(self):
        return self.fetched_table


mock_statuses = make_mock_statuses(user_timeline_json)
mock_statuses2 = make_mock_statuses(user_timeline2_json)
mock_tweet_table = make_mock_tweet_table(mock_statuses)


class TwitterTests(unittest.TestCase):
    def setUp(self):
        super().setUp()

        self.wf_module = MockWfModule()

        self.commit_result_patch = \
            patch('server.modules.moduleimpl.ModuleImpl.commit_result')
        self.commit_result = self.commit_result_patch.start()

    def tearDown(self):
        self.commit_result_patch.stop()

        super().tearDown()

    def test_empty_query(self):
        self.wf_module.querytype = 1
        self.wf_module.query = ''
        Twitter.event(self.wf_module)
        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(error='Please enter a query')
        )

    def test_empty_secret(self):
        self.wf_module.twitter_credentials = None
        Twitter.event(self.wf_module)
        self.commit_result.assert_called_with(
            self.wf_module,
            ProcessResult(error='Please sign in to Twitter')
        )

    @patch('server.oauth.OAuthService.lookup_or_none')
    @patch('tweepy.Cursor')
    def test_user_timeline_accumulate(self, cursor, auth_service):
        self.wf_module.querytype = 0  # user timeline, as opposed to search
        self.wf_module.username = 'foouser'
        self.wf_module.accumulate = True

        instance = cursor.return_value
        instance.pages.return_value = [mock_statuses]

        auth_service.return_value.consumer_key = 'a-key'
        auth_service.return_value.consumer_secret = 'a-secret'

        # Actually fetch!
        Twitter.event(self.wf_module)

        self.commit_result.assert_called()
        result = self.commit_result.call_args[0][1]
        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, mock_tweet_table)

        # now accumulate new tweets
        cursor.reset_mock()
        self.wf_module.fetched_table = result.dataframe
        # add only one tweet, mocking since_id
        instance.pages.return_value = [[mock_statuses2[0]]]
        Twitter.event(self.wf_module)
        self.assertEqual(cursor.call_args[1]['since_id'], mock_statuses[0].id)
        result2 = self.commit_result.call_args[0][1]
        # output should be only new tweets (in this case, one new tweet)
        # appended to old tweets
        self.assertEqual(
            list(result2.dataframe['id']),
            [795018956507582465, 795017539831103489, 795017147651162112]
        )

    @patch('server.oauth.OAuthService.lookup_or_none')
    @patch('tweepy.Cursor')
    def test_accumulate_empty(self, cursor, auth_service):
        # https://www.pivotaltracker.com/story/show/160258591
        # Empty dataframe shouldn't change types
        self.wf_module.accumulate = True

        auth_service.return_value.consumer_key = 'a-key'
        auth_service.return_value.consumer_secret = 'a-secret'

        self.wf_module.fetched_table = mock_tweet_table

        instance = cursor.return_value
        instance.pages.return_value = []

        Twitter.event(self.wf_module)

        self.commit_result.assert_called()
        result = self.commit_result.call_args[0][1]
        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, mock_tweet_table)

    @patch('server.oauth.OAuthService.lookup_or_none')
    @patch('tweepy.Cursor')
    def test_twitter_search(self, cursor, auth_service):
        self.wf_module.querytype = 1
        self.wf_module.query = 'cat'

        auth_service.return_value.consumer_key = 'a-key'
        auth_service.return_value.consumer_secret = 'a-secret'

        instance = cursor.return_value
        instance.items.return_value = mock_statuses

        # Actually fetch!
        Twitter.event(self.wf_module)
        self.commit_result.assert_called()
        result = self.commit_result.call_args[0][1]
        self.assertEqual(result.error, '')
        self.assertEqual(cursor.mock_calls[0][2]['q'], 'cat')

        # Check that render output is right
        assert_frame_equal(result.dataframe, mock_tweet_table)

    @patch('server.oauth.OAuthService.lookup_or_none')
    @patch('tweepy.Cursor')
    def test_twitter_list(self, cursor, auth_service):
        listurl = 'https://twitter.com/thatuser/lists/theirlist'
        self.wf_module.querytype = 2
        self.wf_module.listurl = listurl

        auth_service.return_value.consumer_key = 'a-key'
        auth_service.return_value.consumer_secret = 'a-secret'

        instance = cursor.return_value
        instance.pages.return_value = [mock_statuses]

        # Actually fetch!
        Twitter.event(self.wf_module)
        self.commit_result.assert_called()
        self.assertEqual(cursor.mock_calls[0][2]['owner_screen_name'],
                         'thatuser')
        self.assertEqual(cursor.mock_calls[0][2]['slug'], 'theirlist')

        # Check that render output is right
        result = self.commit_result.call_args[0][1]
        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, mock_tweet_table)
