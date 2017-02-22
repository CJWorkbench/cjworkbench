react-datagrid
=================


### 2.0.1
 * Update `react-menus` dependency to version supporting React `0.14`

### 2.0.0
 * Update to React `0.14` - this is the reason of the major version bump

### 1.2.15
 * Fix sorting grid when column header is touched on touch devices - https://github.com/zippyui/react-datagrid/pull/99

### 1.2.14
 * Fix groupBy bug preventing display of all data in grid (issue #62, fixed in #97)

### 1.2.12
 * move userSelect: none from row inline style to row class

### 1.2.0
 * fix row background to be actually applied to row, not cell
 * add hot loading (`npm run hot`) to the development process.

### 1.1.13
 * add support for column.className to be propagated to column cells.
 * improve testing coverage

### 1.1.0
 * add support for remote data loading and pagination

### 1.0.13
 * add support for Mac meta key on row deselect

### v1.0.5
 * fix selection and row interaction bug introduced by v1.0.4

### v1.0.4
 * fix scrolling issues on Mac (Chrome&Safari)
 * improve scrolling performance on all platforms

### v1.0.1
 * fix bug that did not refresh groupBy grid on column visibility change

### v1.0.0 initial release