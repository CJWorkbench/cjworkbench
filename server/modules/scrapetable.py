from .moduleimpl import ModuleImpl
import pandas as pd
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from server.versions import save_fetched_table_if_changed
from server.sanitizedataframe import sanitize_dataframe
from django.utils.translation import gettext as _
from urllib.error import URLError, HTTPError

class ScrapeTable(ModuleImpl):

    @staticmethod
    def render(wf_module, table):
        table = wf_module.retrieve_fetched_table()
        first_row_is_header = wf_module.get_param_checkbox('first_row_is_header')
        if first_row_is_header:
            table.columns = list(table.iloc[0,:])
            table = table[1:]
        return table

    @staticmethod
    def event(wfm, event=None, **kwargs):
        table = None
        url = wfm.get_param_string('url').strip()
        tablenum = wfm.get_param_integer('tablenum') - 1  # 1 based for user

        if tablenum < 0:
            wfm.set_error(_('Table number must be at least 1'))
            return

        validate = URLValidator()
        try:
            validate(url)
        except ValidationError:
            wfm.set_error(_('That doesn''t seem to be a valid URL'))
            return

        # fetching could take a while so notify clients/users that we're working on it
        wfm.set_busy()

        tables=[]
        try:
            tables = pd.read_html(url, flavor='html5lib')
            if len(tables) == 0:
                wfm.set_error(_('Did not find any <table> tags on that page.'))

        except ValueError as e:
            wfm.set_error(_('No tables found on this page'))
            return

        except HTTPError as e: # catch this first as it's a subclass of URLError
            if e.code == 404:
                wfm.set_error(_('Page not found (404)'))
                return
            else:
                raise e
        except URLError as e:
            wfm.set_error(_('Server not found'))   # bad domain, probably
            return

        numtables = len(tables)
        if numtables == 0:
            wfm.set_error(_('There are no HTML <table> tags on this page'))
            return

        if tablenum >= numtables:
            if numtables == 1:
                wfm.set_error(_('There is only one HTML <table> tag on this page'))
            else:
                wfm.set_error(_('There are only %d HTML <table> tags on this page') % numtables)
            return

        table = tables[tablenum]

        sanitize_dataframe(table) # ensure all columns are simple types (e.g. nested json to strings)

        # Also notifies client
        save_fetched_table_if_changed(wfm, table, '')
