from .moduleimpl import ModuleImpl

# ---- SelectColumns ----

class SelectColumns(ModuleImpl):
    def render(wf_module, table):
        drop_or_keep = wf_module.get_param_menu_idx("drop_or_keep")
        cols = wf_module.get_param_string('colnames').split(',')
        cols = [c.strip() for c in cols]

        # if no column has been selected, keep the columns
        if cols == [] or cols == ['']:
            return table

        # ensure we do not change the order of the columns, even if they are listed in another order
        # this also silently removes any nonexistent columns (can happen when re-ordering module, etc.)
        existing = list(table.columns)
        newcols = []
        for c in existing:
            if c in cols:
                newcols.append(c)

        if drop_or_keep == 1:
            newtab = table[newcols]
        else:
            newtab = table.drop(newcols, axis=1)
        return newtab