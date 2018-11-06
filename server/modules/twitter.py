from collections import namedtuple
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import aiohttp
from aiohttp.client_exceptions import ClientResponseError
from django.utils.translation import gettext as _
import numpy as np
from oauthlib import oauth1
import pandas as pd
from server import oauth
from .moduleimpl import ModuleImpl
from .types import ProcessResult

# Must match order of items in twitter.json module def
QUERY_TYPE_USER = 0
QUERY_TYPE_SEARCH = 1
QUERY_TYPE_LIST = 2


Column = namedtuple('Column', ['name', 'path', 'dtype', 'parse'])


HTML_TAG_RE = re.compile('<[^>]*>')


def parse_source(source: str) -> str:
    """Parse a Twitter Status 'source', to remove HTML tag."""
    return HTML_TAG_RE.sub('', source)


Columns = [
    Column('screen_name', ['user', 'screen_name'], np.object, None),
    Column('created_at', ['created_at'], 'datetime64[ns]', None),
    Column('text', ['full_text'], np.object, None),
    Column('retweet_count', ['retweet_count'], np.int64, None),
    Column('favorite_count', ['favorite_count'], np.int64, None),
    Column('in_reply_to_screen_name', ['in_reply_to_screen_name'], np.object,
           None),
    Column('retweeted_status_screen_name',
           ['retweeted_status', 'user', 'screen_name'], np.object, None),
    Column('source', ['source'], np.object, parse_source),
    Column('id', ['id'], np.int64, None),
]


def create_empty_table():
    data = {}
    for column in Columns:
        data[column.name] = pd.Series([], dtype=column.dtype)
    return pd.DataFrame(data)


def read_raw_value(status: Dict[str, Any], column: Column) -> Any:
    parts = column.path
    raw = status

    try:
        for part in parts:
            raw = raw[part]
    except KeyError:
        raw = None

    return raw


def read_column(statuses: List[Dict[str, Any]], column: Column) -> pd.Series:
    values = [read_raw_value(status, column) for status in statuses]
    series = pd.Series(values, name=column.name)

    if column.parse:
        series = series.map(column.parse)

    series = series.astype(column.dtype)
    return series


def urlencode(component: str):
    """Mimic JavaScript window.encodeURIComponent(component)"""
    return quote(component, safe='')


def _recover_from_160258591(table):
    """Reset types of columns, in-place."""
    # https://www.pivotaltracker.com/story/show/160258591
    for column in Columns:
        try:
            table[column.name] = table[column.name].astype(column.dtype)
        except KeyError:
            pass


# Get dataframe of last tweets fron our storage,
def get_stored_tweets(wf_module):
    table = wf_module.retrieve_fetched_table()
    if table is not None:
        _recover_from_160258591(table)
    return table


async def fetch_from_twitter(access_token, path, since_id: Optional[int],
                             per_page: int,
                             n_pages: int) -> List[Dict[str, Any]]:
    service = oauth.OAuthService.lookup_or_none('twitter_credentials')
    if not service:
        raise Exception('Twitter connection misconfigured')

    oauth_client = oauth1.Client(
        client_key=service.consumer_key,
        client_secret=service.consumer_secret,
        resource_owner_key=access_token['oauth_token'],
        resource_owner_secret=access_token['oauth_token_secret']
    )

    statuses = []

    max_id = None
    async with aiohttp.ClientSession() as session:  # aiohttp timeout of 5min
        for page in range(n_pages):
            # Assume {path} contains '?' already
            page_url = (
                f'https://api.twitter.com/1.1/{path}'
                f'&tweet_mode=extended&count={per_page}'
            )
            if since_id:
                page_url += f'&since_id={since_id}'
            if max_id:
                page_url += f'&max_id={max_id}'

            page_url, headers, _ = oauth_client.sign(
                page_url,
                headers={'Accept': 'application/json'}
            )

            response = await session.get(page_url, headers=headers)
            response.raise_for_status()
            page_statuses = await response.json()

            if isinstance(page_statuses, dict) and 'statuses' in page_statuses:
                # /search wraps result in {}
                page_statuses = page_statuses['statuses']

            if not page_statuses:
                break

            statuses.extend(page_statuses)
            max_id = page_statuses[-1]['id'] - 1

    return statuses


async def twitter_user_timeline(access_token, screen_name,
                                since_id: Optional[int]
                                ) -> List[Dict[str, Any]]:
    # 3200 tweets, aribitrarily
    return await fetch_from_twitter(
        access_token,
        f'statuses/user_timeline.json?screen_name={urlencode(screen_name)}',
        since_id,
        200,
        16
    )


async def twitter_search(access_token, q,
                         since_id: Optional[int]) -> List[Dict[str, Any]]:
    # 1000 tweets, aribitrarily, to try to go easy on rate limits
    # (this is still 10 calls)
    return await fetch_from_twitter(
        access_token,
        f'search/tweets.json?q={urlencode(q)}',
        since_id,
        100,
        10
    )


async def twitter_list_timeline(access_token, owner_screen_name, slug,
                                since_id: Optional[int]
                                ) -> List[Dict[str, Any]]:
    # 2000 tweets, aribitrarily, to try to go easy on rate limits
    # (this is still 10 calls)
    return await fetch_from_twitter(
        access_token,
        (
            'lists/statuses.json'
            f'?owner_screen_name={urlencode(owner_screen_name)}'
            f'&slug={urlencode(slug)}'
        ),
        since_id,
        200,
        5
    )


# Get from Twitter, return as dataframe
async def get_new_tweets(access_token, querytype, query, old_tweets):
    if old_tweets is not None and not old_tweets.empty:
        last_id = old_tweets['id'].max()
    else:
        last_id = None

    if querytype == QUERY_TYPE_USER:
        if query[0] == '@':  # allow user to type @username or username
            query = query[1:]

        # 16 pages of 200 each is Twitter's current maximum archived
        statuses = await twitter_user_timeline(access_token, query, last_id)

    elif querytype == QUERY_TYPE_SEARCH:
        statuses = await twitter_search(access_token, query, last_id)

    else:  # querytype == QUERY_TYPE_LIST
        queryparts = re.search(
            '(?:https?://)twitter.com/([A-Z0-9]*)/lists/([A-Z0-9-_]*)',
            query, re.IGNORECASE
        )
        if not queryparts:
            raise Exception('not a Twitter list URL')

        statuses = await twitter_list_timeline(access_token,
                                               queryparts.group(1),
                                               queryparts.group(2), last_id)

    # Columns to retrieve and store from Twitter
    # Also, we use this to figure out the index the id field when merging old
    # and new tweets
    return pd.DataFrame(dict(
        [(column.name, read_column(statuses, column)) for column in Columns]
    ))


# Combine this set of tweets with previous set of tweets
def merge_tweets(wf_module, new_table):
    old_table = get_stored_tweets(wf_module)

    if old_table is None or old_table.empty:
        return new_table
    elif new_table is None or new_table.empty:
        return old_table
    else:
        # Add in retweeted screen_name if old version doesn't have it (data migration)
        if 'retweeted_status_screen_name' not in old_table.columns:
            old_table.insert(6, 'retweeted_status_screen_name', None)

        return pd.concat([new_table, old_table]) \
                .sort_values('id', ascending=False) \
                .reset_index(drop=True)


class Twitter(ModuleImpl):
    # Render just returns previously retrieved tweets
    @staticmethod
    def render(params, table, *, fetch_result, **kwargs):
        if fetch_result is None:
            return create_empty_table()

        if fetch_result.status == 'error':
            return fetch_result

        if fetch_result.dataframe.empty:
            return create_empty_table()

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
                tweets = await get_new_tweets(access_token, querytype, query,
                                              old_tweets)
                tweets = merge_tweets(wfm, tweets)
            else:
                tweets = await get_new_tweets(access_token, querytype,
                                              query, None)

        except ClientResponseError as err:
            if err.status:
                if querytype == QUERY_TYPE_USER and err.status == 401:
                    return await fail(_('User %s\'s tweets are protected')
                                      % query)
                elif querytype == QUERY_TYPE_USER and err.status == 404:
                    return await fail(_('User %s does not exist') % query)
                elif err.status == 429:
                    return await fail(
                        _('Twitter API rate limit exceeded. '
                          'Please wait a few minutes and try again.')
                    )
                else:
                    return await fail(_('HTTP error %s fetching tweets'
                                        % str(err.status)))
            else:
                return await fail(_('Error fetching tweets: %s' % str(err)))

        result = ProcessResult(dataframe=tweets)

        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()

        await ModuleImpl.commit_result(wfm, result)
