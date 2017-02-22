<!-- File generated from "src/FixedDataTableColumnGroupNew.react.js" -->
`ColumnGroup` (component)
=========================

Component that defines the attributes of a table column group.

Props
-----

### `align`

The horizontal alignment of the table cell content.

type: `enum('left'|'center'|'right')`


### `fixed`

Controls if the column group is fixed when scrolling in the X axis.

type: `bool`
defaultValue: `false`


### `header`

This is the header cell for this column group.
This can either be a string or a React element. Passing in a string
will render a default footer cell with that string. By default, the React
element passed in can expect to receive the following props:

```
props: {
  height: number // (supplied from the groupHeaderHeight)
  width: number // (supplied from the Column)
}
```

Because you are passing in your own React element, you can feel free to
pass in whatever props you may want or need.

You can also pass in a function that returns a react elemnt, with the
props object above passed in as the first parameter.

type: `union(node|func)`

