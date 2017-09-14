from .moduleimpl import ModuleImpl

# ---- SelectColumns ----

class SelectColumns(ModuleImpl):
    def render(wf_module, table):
        drop_or_keep = wf_module.get_param_menu_idx("drop_or_keep")
        cols = wf_module.get_param_string('colnames').split(',')
        cols = [c.strip() for c in cols]

        # if no column has been select, keep the columns
        if cols == [] or cols == ['']:
            return table

        for c in cols:
            if not c in table.columns:
                wf_module.set_error('There is no column named %s' % c)
                return None

        wf_module.set_ready(notify=False)
        if drop_or_keep == 1:
            newtab = table[cols]
        else:
            newtab = table.drop(cols, axis=1)
        return newtab