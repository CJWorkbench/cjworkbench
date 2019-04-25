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
    except EmptyDataError:
        return pd.DataFrame()
    except ParserError as err:
        return str(err)

    # Set default column names: "Column 1", "Column 2", etc.
    table.columns = [f'Column {i + 1}' for i in range(len(table.columns))]

    if params['has_header_row']:
        # Use first row as column names, whenever they're not ''
        header = table.iloc[[0]].T[0].tolist()  # all str, maybe empty
        header = [given or default  # default when given == ''
                  for given, default in zip(header, table.columns)]
        table.columns = header
        # Test for duplicates
        duplicated = table.columns.duplicated()
        if duplicated.any():
            name = table.columns[duplicated][0]
            return (
                f'Duplicate column name "{name}". Please edit the first '
                'line so there are no repeated column names.'
            )
        # Remove header row from content
        table.drop(0, axis=0, inplace=True)
        table.reset_index(drop=True, inplace=True)
        for column in table.columns:
            # Remove header values from category values, if present
            table[column].cat.remove_unused_categories(inplace=True)
    autocast_dtypes_in_place(table)

    return table
