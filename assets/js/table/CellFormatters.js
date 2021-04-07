import { NullCell, TextCell, TimestampCell, makeDateCellComponent, makeNumberCellComponent } from '../BigTable/Cell'

export function columnToCellFormatter (column) {
  if (column.type === 'text') {
    function TextCellFormatter ({ value }) {
      // react-data-grid's cache has a race. sometimes we switch formatters
      // after the data is already switched. When that happens, render null
      // and wait for react-data-grid to render again with the correct formatter
      if (typeof value === 'number') {
        return null
      }
      return <TextCell value={value} />
    }
    return TextCellFormatter
  }

  if (column.type === 'timestamp') {
    function TimestampCellFormatter ({ value }) {
      // react-data-grid's cache has a race. sometimes we switch formatters
      // after the data is already switched. When that happens, render null
      // and wait for react-data-grid to render again with the correct formatter
      if (typeof value === 'number') {
        return null
      }
      return <TimestampCell value={value} />
    }
    return TimestampCellFormatter
  }

  if (column.type === 'number') {
    const NumberCell = makeNumberCellComponent(column.format)
    function NumberCellFormatter ({ value }) {
      // react-data-grid's cache has a race. sometimes we switch formatters
      // after the data is already switched. When that happens, render null
      // and wait for react-data-grid to render again with the correct formatter
      if (typeof value === 'string' || typeof value === 'object') {
        return null
      }

      return <NumberCell value={value} />
    }
    return NumberCellFormatter
  }

  if (column.type === 'date') {
    const DateCell = makeDateCellComponent(column.unit)
    function DateCellFormatter ({ value }) {
      // react-data-grid's cache has a race. sometimes we switch formatters
      // after the data is already switched. When that happens, render null
      // and wait for react-data-grid to render again with the correct formatter
      if (typeof value === 'number') {
        return null
      }

      return <DateCell value={value} />
    }
    return DateCellFormatter
  }

  return NullCell
}
