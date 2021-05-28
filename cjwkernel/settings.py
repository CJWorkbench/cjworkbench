"""
Settings that modules may use to change their behaviors.
"""

MAX_ROWS_PER_TABLE = 1_000_000
"""
How much table can we parse?

Modules must truncate their results to conform to the row-number limit. The
default `render_pandas()` implementation does this.
"""

MAX_COLUMNS_PER_TABLE = 600
"""
How many columns do we allow?

Modules must truncate their results to conform to the column-number limit. The
default `render_pandas()` implementation does this.
"""

MAX_BYTES_PER_VALUE = 32 * 1024
"""
How long can a text value be?

Modules must truncate their values to conform to the cell-size limit.
"""

MAX_CSV_BYTES = 2 * 1024 * 1024 * 1024
"""
What is the largest CSV we dare parse?

Workbench parses into RAM, and a CSV's number of bytes is an upper bound on
the amount of text data within it. This setting restricts the amount of RAM
consumed while parsing a CSV. (RAM fragmentation leads us to consume more
than this in the worst case.)
"""

MAX_BYTES_TEXT_DATA = 1 * 1024 * 1024 * 1024  # 1GB
"""
Maximum number of bytes of UTF-8 text data to hold in memory.

Here's a rough way of calculating the maximum cost of Arrow data for a table:

    8 * MAX_ROWS_PER_TABLE * MAX_COLUMNS_PER_TABLE -- 64 bits per string pointer
    + MAX_BYTES_TEXT_DATA -- actual text
    + [overhead]

While parsing, overhead can amount to 100%. *After* parsing, the Arrow file
is mmapped from disk -- meaning it can consume as little as 0 bytes of RAM.
The file size will roughly agree to the above formula, without much overhead.
"""

MAX_BYTES_PER_COLUMN_NAME = 120
"""
Maximum length of a column name, in UTF-8 bytes.

It is an error for a column name to contain ASCII control characters. Other
than that, anything goes.
"""

MAX_DICTIONARY_PYLIST_N_BYTES = 100_000
"""
Maximum size of a pyarrow.DictionaryType dictionary when opened in Python.

Dictionary data must be read in its entirety, even when slicing a Parquet
file. Lower this limit to reduce _minimum RAM usage_ -- that is, the RAM
needed to read a single value in a column -- even if the outcome increases
_maximum RAM usage_ -- that is, RAM needed to read the entire column.

We use the heuristic: in Python, each string costs 8 bytes for a pointer
plus 50 bytes ... plus the actual UTF-8 bytes within.

(Why tweak this? To reduce the RAM usage of RAM-constrained operations.)
"""

MIN_DICTIONARY_COMPRESSION_RATIO_PYLIST_N_BYTES = 2
"""
Minimum old-size:new-size ratio for us to prefer dictionary encoding.

We use the heuristic: in Python, each string costs 8 bytes for a pointer
plus 50 bytes ... plus the actual UTF-8 bytes within.

Dictionary encoding reduces RAM usage but increases complexity. We only
dictionary-encode when there's good reason.
"""

SCRAPER_NUM_CONNECTIONS = 8
"""
Number of simultaneous requests from urlscraper.
"""

SCRAPER_TIMEOUT = 30
"""
Maximum number of seconds an HTTP request may take.
"""

CHARDET_CHUNK_SIZE = 1024 * 1024
"""
Chunk size for chardet file encoding detection.
"""

SEP_DETECT_CHUNK_SIZE = 1024 * 1024
"""
Number of bytes used when detecting CSV/TSV/??? separator.
"""
