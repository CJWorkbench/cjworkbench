class UnsupportedLocaleError(Exception):
    """An unsupported locale is (attempted to be) used
    
    A locale may be unsupported because its not recognised as a locale
    or because there are no catalogs for it.
    """


class BadCatalogsError(Exception):
    """The catalog for a locale is not properly formatted
    
    A possible formatting error is empty comments at the start of the file.
    """
