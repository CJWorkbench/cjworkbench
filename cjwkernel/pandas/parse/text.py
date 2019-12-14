import cchardet as chardet
import codecs
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import io
from ... import settings


UNICODE_BOM = "\uFFFE"


def detect_encoding(bytesio: io.BytesIO):
    """
    Detect charset, as Python-friendly encoding string.

    Peculiarities:

    * Reads file by CHARDET_CHUNK_SIZE defined in settings.py
    * Stops seeking when detector.done flag True
    * Seeks back to beginning of file for downstream usage
    """
    detector = chardet.UniversalDetector()
    while not detector.done:
        chunk = bytesio.read(settings.CHARDET_CHUNK_SIZE)
        if not chunk:
            break  # EOF
        detector.feed(chunk)

    detector.close()
    bytesio.seek(0)
    return detector.result["encoding"]


@dataclass(frozen=True)
class TranscodeToUtf8Warning:
    encoding: str
    first_invalid_byte: int
    first_invalid_byte_position: int


def transcode_to_utf8_and_warn(
    src: Path, dest: Path, encoding: Optional[str]
) -> Optional[TranscodeToUtf8Warning]:
    """
    Transcode `dest` to UTF-8 if it has a different encoding.

    Remove a starting U+FFFE Unicode byte-order marker, if it exists.

    Recover from errors by inserting U+FFFD. If a recovery occurs, return a
    TranscodeToUtf8Warning.

    Raise LookupError for an `encoding` Python cannot handle.

    Raise UnicodeError upon reaching an unrecoverable error (such as missing
    byte-order marker in "UTF-16").
    """
    BUFFER_SIZE = 1024 * 1024
    warning = None

    with src.open("rb") as src_f, dest.open("wb") as dest_f:
        if encoding is None:
            encoding = detect_encoding(src_f)

        # Start with a `strict` decoder. Judging by codecs.py's innards,
        # we're allowed to change .errors later if we run into an error.
        decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
        decoder.errors = "strict"
        pos = 0  # to build warning

        def decode_and_maybe_warn(buf: bytes, final: bool) -> str:
            nonlocal warning
            try:
                # raise UnicodeError
                return decoder.decode(buf, final)
            except UnicodeDecodeError as err:
                # UnicodeDecodeError we can fix with errors='replace'
                assert decoder.errors == "strict" and warning is None
                decoder_state_buf = decoder.getstate()[0]
                warning = TranscodeToUtf8Warning(
                    encoding=err.encoding,
                    first_invalid_byte=(decoder_state_buf + buf)[err.start],
                    first_invalid_byte_position=(
                        pos - len(decoder_state_buf) + err.start
                    ),
                )
                decoder.errors = "replace"
                return decoder.decode(buf, final)
            # Any other UnicodeError will be raised

        while True:
            buf = src_f.read(BUFFER_SIZE)
            if not len(buf):
                # end of file -- the only way to exit the loop
                s = decode_and_maybe_warn(b"", True)
                dest_f.write(codecs.utf_8_encode(s)[0])
                return warning

            s = decode_and_maybe_warn(buf, False)

            # Remove Unicode byte-order marker (no matter what input encoding)
            if pos == 0 and s[0] == UNICODE_BOM:
                s = s[1:]

            dest_f.write(codecs.utf_8_encode(s)[0])

            pos += len(buf)
