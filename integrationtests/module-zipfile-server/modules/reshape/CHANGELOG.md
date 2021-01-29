2021-01-25.01
-------------

* long-to-wide: repair invalid column names

2020-09-22.01
-------------

* long-to-wide: fix to handle Var="" rows when the Var column is
  compressed as "Categorical". Previously, an error occurred.

2020-09-22.01
-------------

* long-to-wide: fix to correctly ignore (Key=xyz, Var=NULL) rows when
  there is no (Key=xyz, Var=not-null) row the Key column is compressed
  as "Categorical". Previously, an error occurred.

2020-06-23.01
-------------

* Make key columns multi-column.
* Rename fields, for consistency.
