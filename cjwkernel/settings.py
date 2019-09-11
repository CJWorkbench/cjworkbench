"""
Settings that modules may use to change their behaviors.
"""

MAX_ROWS_PER_TABLE = 1_000_000
"""
How much table can we parse?

Modules should truncate their results to conform to the row-number limit. The
default `render_pandas()` implementation does this.
"""

MAX_COLUMNS_PER_TABLE = 500
"""
How many columns do we allow?

Modules should truncate their results to conform to the column-number limit. The
default `render_pandas()` implementation does this.
"""

MAX_PANDAS_BYTES_PER_TABLE = 4.5 * 1024 * 1024 * 1024  # 4.5GB -- mostly str overhead
"""
How many bytes in RAM is a table allowed to take?

Our algorithms use this as an estimate -- they may not be accurate. The intent
is to hint at the module that it may be running out of RAM. If a module ignores
this limit, it may be killed for out-of-memory. (See `MAX_BYTES_RAM`).
"""

MAX_BYTES_RAM = 5 * 1024 * 1024 * 1024  # 5GB
"""
Maximum resident size in memory of a module.

The kernel will kill a module that exceeds this limit; and the user will see an
"out of memory" error.

If a module takes too much RAM, try shrinking it using temporary files and
mmap(). This means using `render_arrow()` instead of `render()` (which uses
RAM-hungry Pandas). `render_arrow()` should only cost a few kilobytes of RAM,
whereas `render()` costs all the user's data.
"""

TWITTER_MAX_ROWS_PER_TABLE = 100_000
"""
Number of tweets allowed.

[2019-05-28] `twitter` deserves its own limit: it's a _common_ module, so
in practice we want to restrict its RAM usage way more than a _rare_
module like `upload`.
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
