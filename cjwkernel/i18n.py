from typing import Dict, Union

from cjwmodule.i18n import I18nMessage


def TODO_i18n(text: str) -> I18nMessage:
    """Build an I18nMessage that "translates" into English only.

    The message has id "TODO_i18n" and one argument, "text", in English.
    Long-term, all these messages should disappear; but this helps us
    migrate by letting us code without worrying about translation.
    """
    return I18nMessage("TODO_i18n", {"text": text}, None)


def trans(
    message_id: str,
    *,
    default: str,
    arguments: Dict[str, Union[int, float, str]] = {},
) -> I18nMessage:
    """Build an I18nMessage, marking it for translation.

    Use this function (instead of constructing `I18nMessage` directly) and the
    string will be marked for translation. Workbench's tooling will extract
    messages from all `trans()` calls and send them to translators.

    The `default` argument informs the translation pipeline; it is not sent
    directly to users on production.
    """
    return I18nMessage(message_id, arguments, None)
