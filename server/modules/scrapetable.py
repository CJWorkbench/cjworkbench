from .moduleimpl import ModuleImpl
import pandas as pd
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from urllib.error import URLError, HTTPError
from .types import ProcessResult


class ScrapeTable(ModuleImpl):
    @staticmethod
    def render(wf_module, table):
        table = wf_module.retrieve_fetched_table()
        first_row_is_header = wf_module.get_param_checkbox('first_row_is_header')
        if first_row_is_header:
            table.columns = list(table.iloc[0, :])
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

        result = None

        try:
            tables = pd.read_html(url, flavor='html5lib')
        except ValueError as e:
            result = ProcessResult(
                error='Did not find any <table> tags on that page'
            )
        except HTTPError as err:  # subclass of URLError
            if err.code == 404:
                result = ProcessResult(error='Page not found (404)')
            else:
                result = ProcessResult(error=str(err))
        except URLError as err:
            result = ProcessResult(error=str(err))

        if not result:
            if len(tables) == 0:
                result = ProcessResult(
                    error='Did not find any <table> tags on that page'
                )
            if tablenum >= len(tables):
                result = ProcessResult(error=(
                    'The maximum table number on this page is '
                    f'{len(tables)}'
                ))

            result = ProcessResult(dataframe=tables[tablenum])

        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()

        ModuleImpl.commit_result(wfm, result)
