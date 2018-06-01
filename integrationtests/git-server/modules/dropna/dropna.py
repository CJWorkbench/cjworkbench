def render(table, params):
		import pandas as pd

		cols = params['colnames'].split(',')
		cols = [c.strip() for c in cols]
		if cols == [] or cols == ['']:
			return table

    # convert empty strings to none, because dropna says '' is not na
		for c in cols:
			if pd.api.types.is_object_dtype(table[c]):  # object -> can have strings in it 
				table[table[c] == ''] = None

		newtab = table.dropna(subset=cols, how='all', axis='index')
		return newtab
