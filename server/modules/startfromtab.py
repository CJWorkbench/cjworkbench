def render(table, params):
    tab = params['tab']

    if tab is None:
        return None

    return tab.dataframe
