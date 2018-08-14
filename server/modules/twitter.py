import tweepy
from tweepy import TweepError
import pandas as pd
import re
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from server import oauth
from django.utils.translation import gettext as _


class Twitter(ModuleImpl):
    # Must match order of items in twitter.json module def
    QUERY_TYPE_USER = 0
    QUERY_TYPE_SEARCH = 1
    QUERY_TYPE_LIST = 2

    # Get dataframe of last tweets fron our storage,
    @staticmethod
    def get_stored_tweets(wf_module):
        return wf_module.retrieve_fetched_table()

    # Get from Twitter, return as dataframe
    @staticmethod
    def get_new_tweets(access_token, querytype, query, old_tweets):
        service = oauth.OAuthService.lookup_or_none('twitter_credentials')
        if not service:
            raise Exception('Twitter connection misconfigured')

        auth = tweepy.OAuthHandler(service.consumer_key,
                                   service.consumer_secret)
        auth.set_access_token(access_token['oauth_token'],
                              access_token['oauth_token_secret'])
        api = tweepy.API(auth)

        if old_tweets is not None and not old_tweets.empty:
            last_id = old_tweets['id'].max()
        else:
            last_id = None

        if querytype == Twitter.QUERY_TYPE_USER:
            if query[0] == '@':                     # allow user to type @username or username
                query = query[1:]

            # 16 pages of 200 each is Twitter's current maximum archived
            statuses = []
            pages = tweepy.Cursor(api.user_timeline, screen_name=query, tweet_mode='extended', since_id=last_id, count=200).pages(16)
            for page in pages:
                statuses.extend([status for status in page])

        elif querytype == Twitter.QUERY_TYPE_SEARCH:

            # 1000 tweets, aribitrarily, to try to go easy on rate limits (this is still 10 calls)
            statuses = list(tweepy.Cursor(api.search, q=query, since_id=last_id, count=100, tweet_mode='extended').items(1000))

        else: # querytype == Twitter.QUERY_TYPE_LIST
            queryparts = re.search('(?:https?://)twitter.com/([A-Z0-9]*)/lists/([A-Z0-9-_]*)', query, re.IGNORECASE)
            if not queryparts:
                raise Exception('not a Twitter list URL')

            # 2000 tweets, aribitrarily, to try to go easy on rate limits (this is still 10 calls)
            statuses = []
            pages = tweepy.Cursor(api.list_timeline, owner_screen_name=queryparts.group(1), slug=queryparts.group(2), since_id=last_id, count=200, tweet_mode='extended').pages(5)
            for page in pages:
                statuses.extend([status for status in page])


        # Columns to retrieve and store from Twitter
        # Also, we use this to figure ou the index the id field when merging old and new tweets
        cols = ['created_at', 'full_text', 'retweet_count', 'favorite_count', 'in_reply_to_screen_name', 'source', 'id']

        tweets = [[getattr(t, x) for x in cols] for t in statuses]
        table = pd.DataFrame(tweets, columns=cols)
        table.insert(0, 'screen_name', [t.user.screen_name for t in statuses])
        # 280 chars should still be called 'text', meh
        table.rename(columns={'full_text': 'text'}, inplace=True)
        return table

    # Combine this set of tweets with previous set of tweets
    def merge_tweets(wf_module, new_table):
        old_table = Twitter.get_stored_tweets(wf_module)
        if old_table is not None:
            new_table = pd.concat([new_table, old_table]) \
                    .sort_values('id', ascending=False) \
                    .reset_index(drop=True)
        return new_table

    # Render just returns previously retrieved tweets
    @staticmethod
    def render(wf_module, table):
        return ProcessResult(
            dataframe=Twitter.get_stored_tweets(wf_module),
            error=wf_module.fetch_error
        )

    # Load specified user's timeline
    @staticmethod
    def event(wfm, **kwargs):
        def fail(error: str) -> None:
            result = ProcessResult(error=error)
            ModuleImpl.commit_result(wfm, result)

        param_names = {
            Twitter.QUERY_TYPE_USER: 'username',
            Twitter.QUERY_TYPE_SEARCH: 'query',
            Twitter.QUERY_TYPE_LIST: 'listurl'
        }

        querytype = wfm.get_param_menu_idx("querytype")
        query = wfm.get_param_string(param_names[querytype])
        access_token = wfm.get_param_secret_secret('twitter_credentials')

        if query.strip() == '':
            return fail('Please enter a query')

        if not access_token:
            return fail('Please sign in to Twitter')

        # fetching could take a while so notify clients/users we're working
        wfm.set_busy(notify=True)

        try:
            if wfm.get_param_checkbox('accumulate'):
                old_tweets = Twitter.get_stored_tweets(wfm)
                tweets = Twitter.get_new_tweets(access_token, querytype, query,
                                                old_tweets)
                tweets = Twitter.merge_tweets(wfm, tweets)
            else:
                tweets = Twitter.get_new_tweets(access_token, querytype, query,
                                                None)

        except TweepError as e:
            if e.response:
                if querytype==Twitter.QUERY_TYPE_USER and e.response.status_code == 401:
                    return fail(_('User %s\'s tweets are protected') % query)
                elif querytype==Twitter.QUERY_TYPE_USER and e.response.status_code == 404:
                    return fail(_('User %s does not exist') % query)
                elif e.response.status_code == 429:
                    return fail(_('Twitter API rate limit exceeded. Please wait a few minutes and try again.'))
                else:
                    return fail(_('HTTP error %s fetching tweets' % str(e.response.status_code)))
            else:
                return fail(_('Error fetching tweets: %s' % str(e)))

        except Exception as e:
            return fail(_('Error fetching tweets: %s' % str(e)))

        result = ProcessResult(dataframe=tweets)

        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()

        ModuleImpl.commit_result(wfm, result)
