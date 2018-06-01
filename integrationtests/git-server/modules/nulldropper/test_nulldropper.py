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
			['fred',			 None,	None,		0,		'',		'2018-1-12'],
			['frederson',	 None,	None,		0,		'',		'2018-1-12 08:15'], 
			['', 					 None, 	None,		0, 		'',		'2018-1-31 5:42'],
			['',					 None,	None,		0,		'',		'1984-7-11'], 
			['maggie',		 None,	None,		0,		'',		'1977-8-12']], 
			columns=['partial','nullobject','nullfloat','zero','emptystring','dates'])

		# Ensure we have the types we want to test
		self.table['partial'] = self.table['partial'].astype(str)
		self.table['nullobject'] = self.table['nullobject'].astype(np.object)
		self.table['nullfloat'] = self.table['nullfloat'].astype(np.object)
		self.table['zero'] = self.table['zero'].astype(np.int64)
		self.table['emptystring'] = self.table['emptystring'].astype(str)
		self.table['dates'] = self.table['dates'].astype(str)

	def test_render(self):
		out = render(self.table, {})
		refcols = ['partial','zero','dates']  # should preserve column order
		self.assertTrue(list(out.columns) == refcols)

if __name__ == '__main__':
    unittest.main()


