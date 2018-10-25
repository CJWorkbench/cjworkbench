import datetime
import tweepy
from tweepy import TweepError
import numpy as np
import pandas as pd
import re
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from server import oauth
from django.utils.translation import gettext as _

# Must match order of items in twitter.json module def
QUERY_TYPE_USER = 0
QUERY_TYPE_SEARCH = 1
QUERY_TYPE_LIST = 2


def _recover_from_160258591(table):
    # https://www.pivotaltracker.com/story/show/160258591
    for column in ['id', 'retweet_count', 'favorite_count']:
        table[column] = table[column].astype(np.int64)
    table['created_at'] = table['created_at'].astype(np.datetime64)


# Get dataframe of last tweets fron our storage,
def get_stored_tweets(wf_module):
    table = wf_module.retrieve_fetched_table()
    if table is not None:
        _recover_from_160258591(table)
    return table


# Get from Twitter, return as dataframe
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

    if querytype == QUERY_TYPE_USER:
        if query[0] == '@':  # allow user to type @username or username
            query = query[1:]

        # 16 pages of 200 each is Twitter's current maximum archived
        statuses = []
        pages = tweepy.Cursor(api.user_timeline, screen_name=query,
                              tweet_mode='extended', since_id=last_id,
                              count=200).pages(16)
        for page in pages:
            statuses.extend([status for status in page])

    elif querytype == QUERY_TYPE_SEARCH:
        # 1000 tweets, aribitrarily, to try to go easy on rate limits
        # (this is still 10 calls)
        statuses = list(tweepy.Cursor(api.search, q=query,
                                      since_id=last_id, count=100,
                                      tweet_mode='extended').items(1000))

    else:  # querytype == QUERY_TYPE_LIST
        queryparts = re.search(
            '(?:https?://)twitter.com/([A-Z0-9]*)/lists/([A-Z0-9-_]*)',
            query, re.IGNORECASE
        )
        if not queryparts:
            raise Exception('not a Twitter list URL')

        # 2000 tweets, aribitrarily, to try to go easy on rate limits
        # (this is still 10 calls)
        statuses = []
        pages = tweepy.Cursor(api.list_timeline,
                              owner_screen_name=queryparts.group(1),
                              slug=queryparts.group(2), since_id=last_id,
                              count=200, tweet_mode='extended').pages(5)
        for page in pages:
            statuses.extend([status for status in page])

    # Columns to retrieve and store from Twitter
    # Also, we use this to figure out the index the id field when merging old
    # and new tweets
    cols = ['created_at', 'full_text', 'retweet_count', 'favorite_count',
            'in_reply_to_screen_name', 'source', 'id']

    tweets = [[getattr(t, x) for x in cols] for t in statuses]
    table = pd.DataFrame(tweets, columns=cols)
    table.insert(0, 'screen_name', [t.user.screen_name for t in statuses])
    # 280 chars should still be called 'text', meh
    table.rename(columns={'full_text': 'text'}, inplace=True)
    return table


# Combine this set of tweets with previous set of tweets
def merge_tweets(wf_module, new_table):
    old_table = get_stored_tweets(wf_module)

    if old_table is None or old_table.empty:
        return new_table
    elif new_table is None or new_table.empty:
        return old_table
    else:
        return pd.concat([new_table, old_table]) \
                .sort_values('id', ascending=False) \
                .reset_index(drop=True)


class Twitter(ModuleImpl):
    # Render just returns previously retrieved tweets
    @staticmethod
    def render(params, table, *, fetch_result, **kwargs):
        if not fetch_result:
            return table

        if fetch_result.status == 'error':
            return fetch_result

        _recover_from_160258591(fetch_result.dataframe)

        return fetch_result

    # Load specified user's timeline
    @staticmethod
    async def fetch(wfm):
        async def fail(error: str) -> None:
            result = ProcessResult(error=error)
            await ModuleImpl.commit_result(wfm, result)

        params = wfm.get_params()

        param_names = {
            QUERY_TYPE_USER: 'username',
            QUERY_TYPE_SEARCH: 'query',
            QUERY_TYPE_LIST: 'listurl'
        }

        querytype = params.get_param_menu_idx("querytype")
        query = params.get_param_string(param_names[querytype])
        access_token = params.get_param_secret_secret('twitter_credentials')

        if query.strip() == '':
            return await fail('Please enter a query')

        if not access_token:
            return await fail('Please sign in to Twitter')

        try:
            if params.get_param_checkbox('accumulate'):
                old_tweets = get_stored_tweets(wfm)
                tweets = get_new_tweets(access_token, querytype, query,
                                        old_tweets)
                tweets = merge_tweets(wfm, tweets)
            else:
                tweets = get_new_tweets(access_token, querytype, query, None)

        except TweepError as e:
            if e.response:
                if querytype == QUERY_TYPE_USER \
                   and e.response.status_code == 401:
                    return await fail(_('User %s\'s tweets are protected')
                                      % query)
                elif querytype == QUERY_TYPE_USER \
                        and e.response.status_code == 404:
                    return await fail(_('User %s does not exist') % query)
                elif e.response.status_code == 429:
                    return await fail(
                        _('Twitter API rate limit exceeded. '
                          'Please wait a few minutes and try again.')
                    )
                else:
                    return await fail(_('HTTP error %s fetching tweets'
                                        % str(e.response.status_code)))
            else:
                return await fail(_('Error fetching tweets: %s' % str(e)))

        result = ProcessResult(dataframe=tweets)

        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()

        await ModuleImpl.commit_result(wfm, result)
