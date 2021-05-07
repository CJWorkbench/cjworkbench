2021-04-22.01
-------------

* Fix off-by-one dates in tooltips
* X axis: support Date columns (in addition to Timestamp columns)

2020-03-18.01
-------------

* (no user-visible change) Use Workbench's new `dataUrl` pattern

2021-03-15.01
-------------

* On multi-series chart, hide Y-axis label by default. (Previously, the first
  series name was used as Y-axis label.)

2021-02-11.01
-------------

* Fix: show custom Y-axis label instead of default

2021-01-20.01
-------------

* HTML: remove 16px margin, to give more control to users

2020-12-15.01
-------------

* HTML: nix obsolete styling of the "ellipsis" button and fix its position.
* Change font to Roboto, to match Workbench.
* Gridlines: use color, not opacity.
* Axes: hide the "domain" line, and color ticks like gridlines.
* Legend: nix top and right padding by reverting to Vega defaults
* Interaction: on hover, highlight the closest X value and all Y values, and
  show their values in a tooltip.

2020-12-14.01
-------------

* Timestamp X axis: detect and special-case "year", "month" and "week" columns.
  Ticks will line up with boundaries.
* Timestamp X axis: always format as UTC (data is always UTC).
* Circle marks: increase size.
* Tooltip: on hover, show a legend with all Y values at the given X value.
* CHANGE: null Y values now appear as "gaps" in their lines. If you are seeing
  gaps you don't want, filter out rows where y=null before creating your
  chart.)

2020-10-02.01
-------------

* (internal) rename "datetime" to "timestamp"
