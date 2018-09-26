"""
This module converts a string column to a datetime column.
Inputting a numerical column will throw an error.
"""
import pandas as pd
import numpy as np


date_input_map = 'AUTO|Date (U.S.) MM/DD/YYYY|Date (E.U.) DD/MM/YYYY'.lower().split('|')

# Map to pd.to_datetime() parameters
input_settings_map = {
    'auto': {
        'infer_datetime_format': True,
        'format': None
    },
    'date (u.s.) mm/dd/yyyy': {
        'infer_datetime_format': False,
        'format': '%m/%d/%Y'
    },
    'date (e.u.) dd/mm/yyyy': {
        'infer_datetime_format': False,
        'format': '%d/%m/%Y'
    }
}

def render(table, params):
    # No processing if no columns selected
    if not params['colnames']:
        return table

    columns = [c.strip() for c in params['colnames'].split(',')]
    type_date = date_input_map[params['type_date']]
    type_null = params['type_null']

    original_table = table.copy()
    error_map = {'first': None}

    for column in columns:
        # For now, re-categorize after replace. Can improve performance by operating
        # directly on categorical index, if needed

        if table[column].dtype.name == 'category':
            table[column] = prep_cat(table[column])
            table[column] = pd.to_datetime(table[column].astype(str), errors='coerce',
                                           format=input_settings_map[type_date]['format'],
                                           infer_datetime_format=input_settings_map[type_date]['infer_datetime_format'],
                                           exact=False, cache=True)
        # For now, assume value is year and cast to string
        elif np.issubdtype(table[column].dtype, np.number):
            table[column] = pd.to_datetime(table[column].astype(str), errors='coerce',
                                           format=input_settings_map[type_date]['format'],
                                           infer_datetime_format=input_settings_map[type_date]['infer_datetime_format'],
                                           exact=False, cache=True)
        # Object
        else:
            table[column] = pd.to_datetime(table[column], errors='coerce',
                                           format=input_settings_map[type_date]['format'],
                                           infer_datetime_format=input_settings_map[type_date]['infer_datetime_format'],
                                           exact=False, cache=True)

        if not type_null:
            error_map = find_errors(table[column], error_map) if error_map['first'] \
                    else find_errors(table[column], error_map, original_table[column])

    if not type_null:
        error_message = display_error(error_map)
        if error_message:
            return (original_table, error_message)

    return table

def prep_cat(series):
    if '' not in series.cat.categories:
        series.cat.add_categories('', inplace=True)
    if any(series.isna()):
            series.fillna('', inplace=True)
    return series

def find_errors(new_series, error_map, old_series=None):
    error_map[new_series.name] = new_series[new_series.isnull()].index

    if type(old_series) == pd.Series and error_map[new_series.name].empty is False:
        error_map['first'] = {
            'column': old_series.name,
            'row': error_map[old_series.name][0] + 1,
            'value': old_series[error_map[old_series.name][0]]
        }

    return error_map

def display_error(error_map):
    num_errors = 0

    for column, errors in error_map.items():
        if column != 'first':
            num_errors += len(errors)

    if num_errors > 0:
        first_column = error_map['first']['column']
        first_row = error_map['first']['row']
        first_value = error_map['first']['value']
        num_columns = len(error_map.keys()) - 1
        return f"'{first_value}' in row {first_row} of '{first_column}' cannot be converted. " \
                f'Overall, there {"are " + str(num_errors) + " errors" if num_errors > 1 else "is " + str(num_errors) + " error"} ' \
                f'in {num_columns} column{"s" if num_columns > 1 else ""}. ' \
                f"Select 'non-dates to null' to set these cells to null"
    return None
