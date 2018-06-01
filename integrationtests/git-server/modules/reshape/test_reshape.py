import unittest
import pandas as pd
from reshape import render
import copy


class TestReshape(unittest.TestCase):

	def setUp(self):
		# this data is designed to sorted in the way that our wide to long operation would sort

		self.long1data = {'date': ['2000-01-03', '2000-01-03', '2000-01-03', '2000-01-04', '2000-01-04', '2000-01-04', '2000-01-05', '2000-01-05', '2000-01-05', '2000-01-06', '2000-01-06', '2000-01-06'],
		 'variable':['George', 'Lisa', 'Michael', 'George', 'Lisa', 'Michael', 'George', 'Lisa', 'Michael', 'George', 'Lisa', 'Michael'],
		 'value':[200, 500, 450, 180.5, 450, 448, 177, 420, 447, 150, 300, 344.6]}

		self.long1 = pd.DataFrame(self.long1data, columns = ['date','variable','value'])

		self.wide1 = self.long1.set_index(['date','variable']).unstack()
		cols = [col[-1] for col in self.wide1.columns.values]
		#cols = ['_'.join(col_tuple) for col_tuple in self.wide1.columns.values]
		self.wide1.columns = cols        # get rid of multi-index hierarchy
		self.wide1 = self.wide1.reset_index() # turn index cols into regular cols

		# Tables with more than one id column
		idcol = pd.Series(['a','b','c','d'])
		idcol.name = 'idcol'
		self.wide2 = pd.concat([idcol, self.wide1], axis=1)

		self.long2 = pd.melt(self.wide2, id_vars=['idcol','date'])
		self.long2.sort_values(['idcol','date'], inplace=True)
		self.long2 = self.long2.reset_index(drop=True)  # renumber after sort, don't add extra index col

		# Testing second key
		self.long3data = self.long1data.copy()
		self.long3data['category'] = ['A'] * 4 + ['B'] * 4 + ['C'] * 4
		self.long3 = pd.DataFrame(self.long3data, columns=['date', 'category', 'variable', 'value'])
		# Result when two keys are supplied
		self.wide3 = self.long3.set_index(['date', 'category', 'variable']).unstack()
		self.wide3.columns = [col[-1] for col in self.wide3.columns.values]
		self.wide3 = self.wide3.reset_index()
		# Result when one key is supplied
		self.wide3single = self.long3.set_index(['date', 'variable']).unstack()
		self.wide3single.columns = [col[-1] for col in self.wide3single.columns.values]
		self.wide3single = self.wide3single.reset_index()

	def test_defaults(self):
		params = { 'direction': 0, 'colnames': '', 'varcol':''}
		out = render(self.wide1, params)
		self.assertTrue(out.equals(self.wide1)) # should NOP when first applied

	def test_wide_to_long(self):
		params = { 'direction': 0, 'colnames': 'date', 'varcol':''}
		out = render(self.wide1, params)
		self.assertTrue(out.equals(self.long1))

	def test_wide_to_long_mulicolumn(self):
		# two ID columns
		params = { 'direction': 0, 'colnames': 'idcol,date', 'varcol':''}
		out = render(self.wide2, params)
		self.assertTrue(out.equals(self.long2))

	def test_long_to_wide(self):
		params = { 'direction': 1, 'colnames': 'date', 'varcol':'variable'}
		out = render(self.long1, params)
		self.assertTrue(out.equals(self.wide1))

	def test_long_to_wide_missing_varcol(self):
		params = { 'direction': 1, 'colnames': 'date', 'varcol':''}
		out = render(self.long1, params)
		self.assertTrue(out.equals(self.long1)) # nop if no column selected

	def test_long_to_wide_second_key(self):
		# If checkbox value not provided, behave like single key
		params = {
			'direction': 1,
			'colnames': 'date',
			'varcol': 'variable'
		}
		out = render(self.long3, params)
		self.assertTrue(out.equals(self.wide3single))

		# If checkbox value is provided but no second key column is
		# specified, behave like single key
		params = {
			'direction': 1,
			'colnames': 'date',
			'has_second_key': True,
			'varcol': 'variable'
		}
		out = render(self.long3, params)
		self.assertTrue(out.equals(self.wide3single))

		# Test two keys
		params = {
			'direction': 1,
			'colnames': 'date',
			'has_second_key': True,
			'second_key': 'category',
			'varcol': 'variable'
		}
		out = render(self.long3, params)
		self.assertTrue(out.equals(self.wide3))

	def test_long_to_wide_mulicolumn(self):
		# two ID columns
		params = { 'direction': 1, 'colnames': 'idcol,date', 'varcol':'variable'}
		out = render(self.long2, params)
		self.assertTrue(out.equals(self.wide2))

	def test_transpose(self):
		# Input simulates a table with misplaced headers
		in_table_data = {
			'Name': ['Date', 'Attr'],
			'Dolores': ['2018-04-22', 10],
			'Robert': ['2016-10-02', None],
			'Teddy': ['2018-04-22', 8]
		}
		ref_table_data = {
			'Name': ['Dolores', 'Robert', 'Teddy'],
			'Date': ['2018-04-22', '2016-10-02', '2018-04-22'],
			'Attr': [10, None, 8]
		}
		in_table = pd.DataFrame(in_table_data, columns=['Name', 'Dolores', 'Robert', 'Teddy'])
		ref_table = pd.DataFrame(ref_table_data, columns=['Name', 'Date', 'Attr'])
		params = {'direction': 2}
		out = render(in_table, params)
		self.assertTrue(out.equals(ref_table))


if __name__ == '__main__':
		unittest.main()
