2021-05-07.01
-------------

* Use Arrow instead of Pandas. Logic remains identical.

2020-09-14.01
-------------

* When a column is renamed to a duplicate, change the name and warn.
  Previously, if you renamed `A` to `B` on a table with columns `[A, B]`,
  you'd get the new table `[B 1, B]` and no warning. Now, you get `[B 2, B]`
  with a warning. (This isn't backwards-compatible; but conflicts are rare,
  consistency with the rest of Workbench's modules is valuable, and warnings
  boost usability and help debug conflicts.)
* When a renamed column name is too long, truncate it and warn.
