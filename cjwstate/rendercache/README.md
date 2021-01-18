Render Cache
============

Stores computations whose results we already know.

Every `render()` function is treated as deterministic; and every time the user
views the output of a `render()` function, the "fresh" value is expected -- so
from the user's perspective, it's as though we ran `render()` anew with each
user request.

Really, we cache the output. Metadata is cached in the database (in `Step`
fields); and tabular data is cached in Parquet files in s3.

This module depends on `cjwstate.models`, `cjwstate.s3` and
`cjwkernel.parquet`.
