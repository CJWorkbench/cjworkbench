from .moduleimpl import ModuleImpl
import pandas as pd
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from server.versions import save_fetched_table_if_changed
from server.utils import sanitize_dataframe
from django.utils.translation import gettext as _
from urllib.error import URLError, HTTPError

class ScrapeTable(ModuleImpl):

    @staticmethod
    def render(wf_module, table):
        return wf_module.retrieve_fetched_table()

    @staticmethod
    def event(wfm, event=None, **kwargs):
        table = None
        url = wfm.get_param_string('url').strip()
        tablenum = wfm.get_param_integer('tablenum') + 1  # 1 based for user

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

        except HTTPError as e: # catch this first as it's a subclass of URLError
            if e.code == 404:
                wfm.set_error(_('Page not found (404)'))
            else:
                raise e
        except URLError as e:
            wfm.set_error(_('Server not found'))   # bad domain, probably

        if wfm.status != wfm.ERROR:
            wfm.set_ready(notify=False)

            tablenum = max(0, min(tablenum, len(tables) - 1))
            table = tables[tablenum]

            # Change the data version (when new data found) only if this module set to auto update, or user triggered
            auto = wfm.auto_update_data or (event is not None and event.get('type') == "click")

            sanitize_dataframe(table) # ensure all columns are simple types (e.g. nested json to strings)

            # Also notifies client
            save_fetched_table_if_changed(wfm, table, auto_change_version=auto)
