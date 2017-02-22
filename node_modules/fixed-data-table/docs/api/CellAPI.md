<!-- File generated from "src/FixedDataTableCellDefault.react.js" -->
`Cell` (component)
==================

Component that handles default cell layout and styling.

All props unless specified below will be set onto the top level `div`
rendered by the cell.

Example usage via from a `Column`:
```
const MyColumn = (
  <Column
    cell={({rowIndex, width, height}) => (
      <Cell
        width={width}
        height={height}
        className="my-class">
        Cell number: <span>{rowIndex}</span>
       </Cell>
    )}
    width={100}
  />
);
```

Props
-----

### `height`

Outer height of the cell.

type: `number`


### `width`

Outer width of the cell.

type: `number`


### `columnKey`

Optional prop that if specified on the `Column` will be passed to the
cell. It can be used to uniquely identify which column is the cell is in.

type: `union(string|number)`

