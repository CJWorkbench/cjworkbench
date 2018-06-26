from django.test import TestCase
from server.sanitizedataframe import *
from pandas.util import hash_pandas_object
import pandas as pd
import os, json

class SantizeDataframeTestCase(TestCase):

    def test_sanitize_dataframe(self):
        # Load a test table which has a dict column
        fname = os.path.join(settings.BASE_DIR, 'server/tests/test_data/sfpd.json')
        sfpd_dict = json.load(open(fname))
        sfpd = pd.DataFrame(sfpd_dict)

        sfpd_types = sfpd.apply(pd.api.types.infer_dtype)
        self.assertEqual(sfpd.columns[6], 'location')
        self.assertEqual(sfpd_types[6], 'mixed')

        sanitize_dataframe(sfpd)

        # should have converted mixed types (and other complex types) to string
        sfpd_types = sfpd.apply(pd.api.types.infer_dtype)
        self.assertEqual(sfpd_types[6], 'string')

        # used by StoredObject, will crash on complex types, which we should not have
        hash_pandas_object(sfpd)


    def test_nan_to_string(self):
        # check that sanitizing a non-string column with missing data produces empty cells, not 'nan' strings
        # https://www.pivotaltracker.com/story/show/154619564
        fname = os.path.join(settings.BASE_DIR, 'server/tests/test_data/missing_values.json')
        mv_json = open(fname).read()
        mv_table = pd.DataFrame(json.loads(mv_json))
        sanitize_dataframe(mv_table)
        numempty = sum(mv_table['recording_date'].apply(lambda x: x==''))
        self.assertTrue(numempty > 0)


    def test_lists_and_dicts(self):
        # By assigning through Series it is possible to store lists and dicts in a DataFrame.
        # True fact. Fucks people up. But not us.
        t = pd.DataFrame([[1, 2, 3],[4,5,6]], columns=['a','b','c'])
        s = pd.Series([None, None])
        s[0] = [5,6,7]
        s[1] = {8:9}
        t['s']=s
        sanitize_dataframe(t)
        self.assertEqual(t['s'][0], '[5, 6, 7]')
        self.assertEqual(t['s'][1], '{8: 9}')


    def test_duplicate_colnames(self):
        # check that duplicate cols are renamed, and that non-string names are converted to string
        t = pd.DataFrame([[1, 2, 3],[4,5,6]], columns=['a',20.0,'a'])
        sanitize_dataframe(t)
        self.assertEqual(list(t.columns), ['a','20','a_1'])


    def test_reset_index(self):
        # should always come out with row numbers contiguous from zero
        table = pd.DataFrame([[1, 'a'],[2, 'b'],[3, 'c']])
        newtab = pd.concat([table.iloc[0:0], table.iloc[1:]])  # lose middle row, makes index non contiguous
        sanitize_dataframe(newtab)
        self.assertCountEqual((newtab.index), [0,1])