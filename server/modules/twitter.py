import tweepy
import pandas as pd
from datetime import timedelta
from django.utils import timezone
import requests
import time
import os
import csv
import io
from .moduleimpl import ModuleImpl
from server.models import ChangeDataVersionCommand

# ---- Twitter ----

class Twitter(ModuleImpl):

    # Get dataframe of last tweets fron our storage,
    @staticmethod
    def get_stored_tweets(wf_module):
        tablestr = wf_module.retrieve_data()
        if (tablestr != None) and (len(tablestr) > 0):
            return pd.read_csv(io.StringIO(tablestr))
        else:
            return None

    # Get from Twitter, return as dataframe
    @staticmethod
    def get_new_tweets(wfm, querytype, query, old_tweets):

        # Authenticate with "app authentication" mode (high rate limit, read only)
        consumer_key = os.environ['CJW_TWITTER_CONSUMER_KEY']
        consumer_secret = os.environ['CJW_TWITTER_CONSUMER_SECRET']
        auth = tweepy.AppAuthHandler(consumer_key, consumer_secret)
        api = tweepy.API(auth)

        if querytype == 'User':
            tweetsgen = api.user_timeline(query, count=200)
        else:
            # Only get last 24 hours of tweets, because we have to bound this somehow
            today = timezone.today()
            yesterday = today - timedelta(1)
            date_clause = " since:{0}-{1}-{2} until:{3}-{4}-{5}".format(
                yesterday.year, yesterday.month, yesterday.day,
                today.year, today.month, today.day)

            tweetsgen = api.search(query + date_clause)

        # Columns to retrieve and store from Twitter
        # Also, we use this to figure ou the index the id field when merging old and new tweets
        cols = ['id', 'created_at', 'text', 'in_reply_to_screen_name', 'in_reply_to_status_id', 'retweeted',
                'retweet_count', 'favorited', 'favorite_count', 'source']

        tweets = [[getattr(t, x) for x in cols] for t in tweetsgen]
        table = pd.DataFrame(tweets, columns=cols)
        return table


    # Combine this set of tweets with previous set of tweets
    def merge_tweets(wf_module, new_table):
        old_table = Twitter.get_stored_tweets(wf_module)
        if old_table != None:
            new_table = pd.concat([new_table,old_table]).drop_duplicates().sort_values('id',ascending=False).reset_index(drop=True)
        return new_table

    # Render just returns previously retrieved tweets
    @staticmethod
    def render(wf_module, table):
        return Twitter.get_stored_tweets(wf_module)


    # Load specified user's timeline
    @staticmethod
    def event(wfm, parameter, e):
        table = None

        # fetching could take a while so notify clients/users that we're working on it
        wfm.set_busy(notify=True)
        querytype = wfm.get_param_menu_string('querytype')
        query = wfm.get_param_string('query')

        try:

            if wfm.get_param_checkbox('accumulate'):
                old_tweets = Twitter.get_stored_tweets(wfm)
                tweets = Twitter.get_new_tweets(wfm, querytype, query, old_tweets)
                tweets = Twitter.merge_tweets(wfm, tweets)
            else:
                tweets = Twitter.get_new_tweets(wfm, querytype, query, None)

        except requests.exceptions.HTTPError as e:
            if querytype=='User' and e.response.status_code==401:
                wfm.set_error('User %s\'s tweets are protected' % query)
                wfm.store_text('csv', '')
                return
            elif querytype=='User'and response.status_code==404:
                wfm.set_error('User %s does not exist' % query)
                wfm.store_text('csv', '')
                return
            else:
                wfm.set_error('HTTP rrror %s fetching tweets' % str(res.status_code))
                wfm.store_text('csv', '')
                return

        except Exception as e:
            wfm.set_error('Error fetching tweets: ' + str(e))
            wfm.store_text('csv', '')
            return

        # we are done. save fetched data, and switch to it
        version = wfm.store_data(tweets.to_csv(index=False)) # index=False to prevent pandas from adding an index col
        ChangeDataVersionCommand.create(wfm, version)  # also notifies client

