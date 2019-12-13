from cjwkernel.types import I18nMessage


__all__ = ["HttpError"]


class HttpError(Exception):
    """
    An HTTP request did not complete.
    """

    @property
    def i18n_message(self) -> I18nMessage:
        return I18nMessage.TODO_i18n(self.args[0])


class HttpErrorTimeout(HttpError):
    def __init__(self):
        return super().__init__("HTTP request timed out.")


class HttpErrorInvalidUrl(HttpError):
    def __init__(self):
        return super().__init__(
            "Invalid URL. Please supply a valid URL, starting with http:// or https://."
        )


class HttpErrorTooManyRedirects(HttpError):
    def __init__(self):
        return super().__init__(
            "HTTP server(s) redirected us too many times. Please try a different URL."
        )


class HttpErrorClientResponseError(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return I18nMessage.TODO_i18n(
            "Error from server: HTTP %d %s"
            % (self.__cause__.status, self.__cause__.message)
        )


class HttpErrorClientError(HttpError):
    # override
    @property
    def i18n_message(self) -> I18nMessage:
        return I18nMessage.TODO_i18n(
            "Error during HTTP request: %s" % str(self.__cause__)
        )


HttpError.Timeout = HttpErrorTimeout
HttpError.ClientError = HttpErrorClientError
HttpError.InvalidUrl = HttpErrorInvalidUrl
HttpError.ClientResponseError = HttpErrorClientResponseError
HttpError.TooManyRedirects = HttpErrorTooManyRedirects
