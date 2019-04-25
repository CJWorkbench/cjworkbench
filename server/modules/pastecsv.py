import io
import pandas as pd
from pandas.io.common import EmptyDataError, ParserError
from .utils import autocast_dtypes_in_place


def render(table, params):
    tablestr: str = params['csv']
    has_header_row: bool = params['has_header_row']

    # Guess at format by counting commas and tabs
    n_commas = tablestr.count(',')
    n_tabs = tablestr.count('\t')
    if n_commas > n_tabs:
        sep = ','
    else:
        sep = '\t'

    try:
        table = pd.read_csv(io.StringIO(tablestr), header=None,
                            skipinitialspace=True, sep=sep,
                            na_filter=False, dtype='category',
                            index_col=False, engine='python')

        if params['has_header_row']:
            table.columns = table.iloc[[0]].astype(str).T[0].array
            table.drop(0, axis=0, inplace=True)
            table.reset_index(drop=True, inplace=True)
            # Remove header values from category values
            for column in table.columns:
                table[column].cat.remove_unused_categories(inplace=True)
        else:
            table.columns = [f'Column {i + 1}'
                             for i in range(len(table.columns))]

        autocast_dtypes_in_place(table)
    except EmptyDataError:
        return pd.DataFrame()
    except ParserError as err:
        print(repr(err))
        return str(err)

    return table
