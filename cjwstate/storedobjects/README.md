Stored Objects
==============

*EVIL* -- store fetch() outputs as DataFrames.

Really, we want fetch() output to be whatever the module _wants_ it to be. But
for legacy reasons, our database is filled with DataFrames instead of raw data.

StoredObjects are stored in the database, and they point to minio.

This module depends on `cjwstate.models`, `cjwstate.minio` and
`cjwstate.parquet`.
