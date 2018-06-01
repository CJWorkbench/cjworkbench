import unittest
import pandas as pd
import numpy as np
from dropna import render

class TestDropNA(unittest.TestCase):
 
	def setUp(self):
		# Test data includes:
		#  - rows of numeric and string types
		#  - zero entries (which should not be removed)
		#  - some partially and some completely empty rows
		self.table = pd.DataFrame([
			['fred',			2,			3.14,		'2018-1-12'],
			['frederson',	5,			None,		'2018-1-12 08:15'], 
			['', 					-10, 		None, 	''],
			['',					-2,			10,			''], 
			['maggie',		8,			0,			'1984-7-11']], 
			columns=['stringcol','intcol','floatcol','datecol'])

		# Pandas should infer these types anyway, but leave nothing to chance
		self.table['stringcol'] = self.table['stringcol'].astype(str)
		self.table['intcol'] = self.table['intcol'].astype(np.int64)
		self.table['floatcol'] = self.table['floatcol'].astype(np.float64)
		self.table['datecol'] = self.table['datecol'].astype(str)

	def test_NOP(self):
		params = { 'colnames': ''}
		out = render(self.table, params)
		self.assertTrue(out.equals(self.table)) # should NOP when first applied

	def test_numeric(self):
		params = { 'colnames': 'intcol'}
		out = render(self.table, params)
		ref = self.table[[True, True, True, True, True]]  # also tests no missing
		self.assertTrue(out.equals(ref))

		params = { 'colnames': 'floatcol'}
		out = render(self.table, params)
		ref = self.table[[True, False, False, True, True]]
		self.assertTrue(out.equals(ref))

	def test_string(self):
		params = { 'colnames': 'stringcol'}
		out = render(self.table, params)
		ref = self.table[[True, True, False, False, True]]
		self.assertTrue(out.equals(ref))

	def test_multiple_colnames(self):
		params = { 'colnames': 'intcol,floatcol'}
		out = render(self.table, params)
		self.assertTrue(out.equals(self.table))  # no drop b/c int has no empty vals

if __name__ == '__main__':
    unittest.main()


