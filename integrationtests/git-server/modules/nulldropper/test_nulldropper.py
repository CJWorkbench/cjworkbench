import unittest
import pandas as pd
import numpy as np
from nulldropper import render

class TestDropNullColumns(unittest.TestCase):
 
	def setUp(self):
		# Test data includes:
		#  - null cols of object type
		#  - entirely NaN column of floats
		#  - partially empty columns
		#  - column of empty strings (should be dropped)
		#  - column of zeros (which should not be dropped)
		self.table = pd.DataFrame([
			['fred',			 None,	None,		0,		'','',None,		'2018-1-12', 'a'],
			['frederson',	 None,	None,		0,		'','',None,		'2018-1-12 08:15', 'b'],
			['', 					 None, 	None,		0, 		'','',None,		'2018-1-31 5:42', 'c'],
			['',					 None,	None,		0,		'','',None,		'1984-7-11', 'd'],
			['maggie',		 None,	None,		0,		'','',None,		'1977-8-12', 'e']],
			columns=['partial','nullobject','nullfloat','zero','emptystring','emptycat','nonecat','dates','categories'])

		# Ensure we have the types we want to test
		self.table['partial'] = self.table['partial'].astype(str)
		self.table['nullobject'] = self.table['nullobject'].astype(np.object)
		self.table['nullfloat'] = self.table['nullfloat'].astype(np.object)
		self.table['zero'] = self.table['zero'].astype(np.int64)
		self.table['emptystring'] = self.table['emptystring'].astype(str)
		self.table['dates'] = self.table['dates'].astype(str)
		self.table['emptycat'] = self.table['emptycat'].astype('category')
		self.table['categories'] = self.table['categories'].astype('category')
		self.table['nonecat'] = self.table['nonecat'].astype('category')

	def test_render(self):
		out = render(self.table, {})
		refcols = ['partial','zero','dates', 'categories']  # should preserve column order
		self.assertTrue(list(out.columns) == refcols)

if __name__ == '__main__':
    unittest.main()


