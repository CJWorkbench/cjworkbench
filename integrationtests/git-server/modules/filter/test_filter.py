import unittest
import pandas as pd
from filter import render

# turn menu strings into indices for parameter dictionary
# must be kept in sync with filter.json
menutext = "Select||Text contains|Text does not contain|Text is exactly||Cell is empty|Cell is not empty||Equals|Greater than|Greater than or equals|Less than|Less than or equals||Date is|Date is before|Date is after||Filter by text"
menu = menutext.split('|')

# keep menu
keeptext = 'Keep|Drop'
keepmenu = keeptext.split('|')


class TestFilter(unittest.TestCase):

	def setUp(self):
		# Test data includes some partially and completely empty rows because this tends to freak out Pandas
		self.table = pd.DataFrame(
			[['fred', 2, 3, 'round', '2018-1-12'],
			['frederson', 5, None, 'square', '2018-1-12 08:15'],
			[None, None, None, None, None],
			['maggie', 8, 10, 'Round', '2015-7-31'],
			['Fredrick', 5, None, 'square', '2018-3-12']],
			columns=['a', 'b', 'c', 'd', 'date'])

	def test_no_column(self):
		params = {'column': '', 'condition': 0, 'value': ''}
		out = render(self.table, params)
		self.assertTrue(out.equals(self.table))  # should NOP when first applied

	def test_no_condition(self):
		params = {
			'column': 'a',
			'condition': menu.index('Select')
		}
		out = render(self.table, params)
		self.assertTrue(out.equals(self.table))

	def test_no_value(self):
		params = {'column': 'a', 'condition': 0, 'value': ''}
		out = render(self.table, params)
		self.assertTrue(out.equals(self.table))  # should NOP if no value

	def test_contains(self):
		# Case-insensitive, no regex, keep
		params = {
			'column': 'a',
			'condition': menu.index('Text contains'),
			'value': 'fred',
			'casesensitive': False,
			'regex': False,
			'keep': keepmenu.index('Keep')
		}
		out = render(self.table, params)
		ref = self.table[[True, True, False, False, True]]
		self.assertTrue(out.equals(ref))

		# Case-sensitive, no regex, keep
		params = {
			'column': 'a',
			'condition': menu.index('Text contains'),
			'value': 'fred',
			'casesensitive': True,
			'regex': False,
			'keep': keepmenu.index('Keep')
		}
		out = render(self.table, params)
		ref = self.table[[True, True, False, False, False]]
		self.assertTrue(out.equals(ref))

		# Case-sensitive, regex, keep
		params = {
			'column': 'a',
			'condition': menu.index('Text contains'),
			'value': 'f[a-zA-Z]+d',
			'casesensitive': True,
			'regex': True,
			'keep': keepmenu.index('Keep')
		}
		out = render(self.table, params)
		ref = self.table[[True, True, False, False, False]]
		self.assertTrue(out.equals(ref))

		# Case-sensitive, regex, drop
		params = {
			'column': 'a',
			'condition': menu.index('Text contains'),
			'value': 'f[a-zA-Z]+d',
			'casesensitive': True,
			'regex': True,
			'keep': keepmenu.index('Drop')
		}
		out = render(self.table, params)
		ref = self.table[[False, False, True, True, True]]
		self.assertTrue(out.equals(ref))

	def test_not_contains(self):
		# Case-insensitive, no regex, keep
		params = {
			'column': 'a',
			'condition': menu.index('Text does not contain'),
			'value': 'fred',
			'casesensitive': False,
			'regex': False,
			'keep': keepmenu.index('Keep')
		}
		out = render(self.table, params)
		ref = self.table[[False, False, True, True, False]]
		self.assertTrue(out.equals(ref))

		# Case-sensitive, no regex, keep
		params = {
			'column': 'a',
			'condition': menu.index('Text does not contain'),
			'value': 'fred',
			'casesensitive': True,
			'regex': False,
			'keep': keepmenu.index('Keep')
		}
		out = render(self.table, params)
		ref = self.table[[False, False, True, True, True]]
		self.assertTrue(out.equals(ref))

		# Case-sensitive, regex, keep
		params = {
			'column': 'a',
			'condition': menu.index('Text does not contain'),
			'value': 'f[a-zA-Z]+d',
			'casesensitive': True,
			'regex': True,
			'keep': keepmenu.index('Keep')
		}
		out = render(self.table, params)
		ref = self.table[[False, False, True, True, True]]
		self.assertTrue(out.equals(ref))

		# Case-sensitive, regex, drop
		params = {
			'column': 'a',
			'condition': menu.index('Text does not contain'),
			'value': 'f[a-zA-Z]+d',
			'casesensitive': True,
			'regex': True,
			'keep': keepmenu.index('Drop')
		}
		out = render(self.table, params)
		ref = self.table[[True, True, False, False, False]]
		self.assertTrue(out.equals(ref))

	def test_exactly(self):
		params = {
			'column': 'a',
			'condition': menu.index('Text is exactly'),
			'value': 'fred',
			'casesensitive': True,
			'regex': False,
			'keep': keepmenu.index('Keep')
		}
		out = render(self.table, params)
		ref = self.table[[True, False, False, False, False]]
		self.assertTrue(out.equals(ref))

		params = {
			'column': 'd',
			'condition': menu.index('Text is exactly'),
			'value': 'round',
			'casesensitive': False,
			'regex': False,
			'keep': keepmenu.index('Keep')
		}
		out = render(self.table, params)
		ref = self.table[[True, False, False, True, False]]
		self.assertTrue(out.equals(ref))

		# Do numeric equals on a numeric column
		params = {'column': 'b',
			'condition': menu.index('Text is exactly'),
			'casesensitive': False,
			'regex': False,
			'value': 5,
			'keep': keepmenu.index('Keep')}
		out = render(self.table, params)
		ref = self.table[[False, True, False, False, True]]
		self.assertTrue(out.equals(ref))

	def test_empty(self):
		params = {'column': 'c', 'condition': menu.index(
		'Cell is empty'), 'value': 'nonsense'}
		out = render(self.table, params)
		ref = self.table[[False, True, True, False, True]]
		self.assertTrue(out.equals(ref))

		# should not require value
		params = {'column': 'c', 'condition': menu.index(
		'Cell is empty'), 'value': ''}
		out = render(self.table, params)
		self.assertTrue(out.equals(ref))

	def test_not_empty(self):
		params = {'column': 'c', 'condition': menu.index(
		'Cell is not empty'), 'value': 'nonsense'}
		out = render(self.table, params)
		ref = self.table[[True, False, False, True, False]]
		self.assertTrue(out.equals(ref))

		# should not require value
		params = {'column': 'c', 'condition': menu.index(
		'Cell is not empty'), 'value': ''}
		out = render(self.table, params)
		self.assertTrue(out.equals(ref))

	def test_equals(self):
		# working as intended
		params = {
			'column': 'c',
			'condition': menu.index('Equals'),
			'value': '3'
		}
		out = render(self.table, params)
		ref = self.table[[True, False, False, False, False]]
		self.assertTrue(out.equals(ref))

		# non-numeric column should return error message
		params = {
			'column': 'a',
			'condition': menu.index('Equals'),
			'value': '3'
		}
		out = render(self.table, params)
		self.assertTrue(isinstance(out, str))  # should return error message

		# non-numeric column should return error message
		params = {
			'column': 'date',
			'condition': menu.index('Equals'),
			'value': '3'
		}
		out = render(self.table, params)
		self.assertTrue(isinstance(out, str))  # should return error message

		# non-numeric value should return error message
		params = {
			'column': 'c',
			'condition': menu.index('Equals'),
			'value': 'gibberish'
		}
		out = render(self.table, params)
		self.assertTrue(isinstance(out, str))  # should return error message

	def test_greater(self):
		# edge case, first row has b=2
		params = {
			'column': 'b',
			'condition': menu.index('Greater than'),
			'value': '2'
		}
		out = render(self.table, params)
		ref = self.table[[False, True, False, True, True]]
		self.assertTrue(out.equals(ref))

	def test_greater_equals(self):
		# edge case, first row has b=2
		params = {
			'column': 'b',
			'condition': menu.index('Greater than or equals'),
			'value': '2'
		}
		out = render(self.table, params)
		ref = self.table[[True, True, False, True, True]]
		self.assertTrue(out.equals(ref))

	def test_less(self):
		# edge case, second and last row has b=5
		params = {
			'column': 'b',
			'condition': menu.index('Less than'),
			'value': '5'
		}
		out = render(self.table, params)
		ref = self.table[[True, False, False, False, False]]
		self.assertTrue(out.equals(ref))

	def test_less_equals(self):
		# edge case, second and last row has b=5
		params = {
			'column': 'b',
			'condition': menu.index('Less than or equals'),
			'value': '5'
		}
		out = render(self.table, params)
		ref = self.table[[True, True, False, False, True]]
		self.assertTrue(out.equals(ref))

	def test_date_is(self):
		params = {
			'column': 'date',
			'condition': menu.index('Date is'),
			'value': '2015-7-31'
		}
		out = render(self.table, params)
		ref = self.table[[False, False, False, True, False]]
		self.assertTrue(out.equals(ref))

	def test_bad_date(self):
		# columns that aren't dates -> error
		params = {'column': 'a', 'condition': menu.index(
		'Date is'), 'value': '2015-7-31'}
		out = render(self.table, params)
		self.assertTrue(isinstance(out, str))  # should return error message

		params = {'column': 'b', 'condition': menu.index(
		'Date is'), 'value': '2015-7-31'}
		out = render(self.table, params)
		self.assertTrue(isinstance(out, str))

		# stirng that isn't a date -> error
		params = {'column': 'date', 'condition': menu.index(
		'Date is'), 'value': 'gibberish'}
		out = render(self.table, params)
		self.assertTrue(isinstance(out, str))

	def test_date_before(self):
		params = {'column': 'date', 'condition': menu.index(
		'Date is before'), 'value': '2016-7-31'}
		out = render(self.table, params)
		ref = self.table[[False, False, False, True, False]]
		self.assertTrue(out.equals(ref))

	def test_date_after(self):
		# edge case, first row is 2018-1-12 08:15 so after implied midnight of date without time
		params = {'column': 'date', 'condition': menu.index(
		'Date is after'), 'value': '2018-1-12'}
		out = render(self.table, params)
		ref = self.table[[False, True, False, False, True]]
		self.assertTrue(out.equals(ref))


if __name__ == '__main__':
	unittest.main()
