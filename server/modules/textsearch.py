from .moduleimpl import ModuleImpl


# ---- TextSearch ----
# Returns only those rows which contain the query string in any of the specified columns

class TextSearch(ModuleImpl):
    def render(wf_module, table):
        query = wf_module.get_param_string('query')
        cols = wf_module.get_param_string('colnames').split(',')
        cols = [c.strip() for c in cols]
        case_sensitive = wf_module.get_param_checkbox('casesensitive')
        regex = wf_module.get_param_checkbox('regex')

        if cols == ['']:
            return None     # no columns, no matches

        if query=='':
            return table    # no query, everything matches

        keeprows = None
        for c in cols:
            if not c in table.columns:
                wf_module.set_error('There is no column named %s' % c)
                return None

            kr = table[c].astype(str).str.contains(query, case=case_sensitive, regex=regex)

            # logical OR of all matching columns
            if keeprows is not None:
                keeprows = keeprows | kr
            else:
                keeprows = kr

        newtab = table[keeprows]
        wf_module.set_ready(notify=False)
        return newtab