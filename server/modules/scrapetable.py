from .moduleimpl import ModuleImpl
import pandas as pd
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from urllib.error import URLError, HTTPError
from .types import ProcessResult


def merge_colspan_headers_in_place(table) -> None:
    """
    Pandas read_html() returns tuples for column names when scraping tables with colspan.
    This collapses duplicate entries and reformats to be human readable.
    E.g. ('year', 'year') -> 'year' and ('year', 'month') -> 'year - month'

    Alters the table in place, no return value.
    """

    newcols = []
    for c in table.columns:
        if isinstance(c, tuple):
            # collapse all runs of duplicate values: 'a','a','b','c','c','c' -> 'a','b','c'
            vals = list(c)
            idx = 0
            while idx < len(vals)-1:
                if vals[idx]==vals[idx+1]:
                    vals.pop(idx)
                else:
                    idx += 1
            # put dashes between all remaining header values
            newcols.append(' - '.join(vals))
        else:
            newcols.append(c)
    table.columns = newcols


class ScrapeTable(ModuleImpl):
    @staticmethod
    def render(params, table, *, fetch_result, **kwargs):
        if not fetch_result:
            return table

        if fetch_result.status == 'error':
            return fetch_result

        table = fetch_result.dataframe

        if params.get_param_checkbox('first_row_is_header'):
            table.columns = [str(c) for c in list(table.iloc[0, :])]
            table = table[1:]
            table.reset_index(drop=True, inplace=True)

        return (table, fetch_result.error)

    @staticmethod
    async def event(wfm, **kwargs):
        async def fail(error: str) -> None:
            result = ProcessResult(error=error)
            await ModuleImpl.commit_result(wfm, result)

        params = wfm.get_params()

        table = None
        url = params.get_param_string('url').strip()
        tablenum = params.get_param_integer('tablenum') - 1  # 1 based for user

        if tablenum < 0:
            return await fail(_('Table number must be at least 1'))

        validate = URLValidator()
        try:
            validate(url)
        except ValidationError:
            return await fail(_('Invalid URL'))

        result = None

        try:
            # TODO async HTML fetch
            tables = pd.read_html(url, flavor='html5lib')
        except ValueError as e:
            result = ProcessResult(
                error=_('Did not find any <table> tags on that page')
            )
        except HTTPError as err:  # subclass of URLError
            if err.code == 404:
                result = ProcessResult(error=_('Page not found (404)'))
            else:
                result = ProcessResult(error=str(err))
        except URLError as err:
            result = ProcessResult(error=str(err))

        if not result:
            if not tables:
                result = ProcessResult(
                    error=_('Did not find any <table> tags on that page')
                )
            elif tablenum >= len(tables):
                result = ProcessResult(error=(
                    _('The maximum table number on this page is %d') % len(tables)
                ))
            else:
                table = tables[tablenum]
                merge_colspan_headers_in_place(table)
                result = ProcessResult(dataframe=table)

        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()

        await ModuleImpl.commit_result(wfm, result)
