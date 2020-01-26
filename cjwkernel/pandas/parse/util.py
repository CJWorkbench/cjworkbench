from cjwkernel.types import I18nMessage


def invalid_encoding_i18n_message(
    first_invalid_byte: int,
    first_invalid_byte_position: int,
    encoding: str,
    replacement: str,
) -> I18nMessage:
    return I18nMessage.trans(
        "py.cjwkernell.pandas.parse.util.invalid_encoding_i18n_message",
        default=(
            "Encoding error: byte {byte} is invalid {encoding} at byte {byte_position}. "
            "We replaced invalid bytes with “{replacement}”."
        ),
        args={
            "byte": "0x%02X" % first_invalid_byte,
            "encoding": encoding,
            "byte_position": first_invalid_byte_position,
            "replacement": replacement,
        },
    )
