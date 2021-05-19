import React from 'react'
import PropTypes from 'prop-types'
import useThrottledRequestAnimationFrame from './useThrottledRequestAnimationFrame'
import Table from './Table'
import { useFocusCell } from './state'

function getRowThMeasurementsFromTbody (tbody) {
  if (tbody === null) {
    return null
  }
  const cell1 = tbody.querySelector('tr:not(.updating)>th')
  if (!cell1) {
    // We must be redrawing? There should _always_ be a focal range, because
    // we started with non-empty (see useFocalCells.js) and there's no way to
    // revert to non-empty.
    return null
  }
  if (cell1.offsetParent === null) {
    // We're display:none. No need to resize.
    return null
  }
  const cell1Rect = cell1.getBoundingClientRect()
  return {
    thWidth: cell1Rect.width,
    rowHeight: cell1Rect.height / cell1.rowSpan
  }
}

export default function Viewport ({
  nRows,
  columns,
  cells,
  nSkipRows,
  nSkipColumns,
  setFocusCellRange,
  onEdit
}) {
  const focusCell = useFocusCell()
  const [viewport, setViewport] = React.useState(null)
  const [tbody, setTbody] = React.useState(null)
  const columnOffsetsAfterTh = React.useMemo(() => {
    const ret = new Array(columns.length).fill(0)
    let x = 0
    columns.forEach((column, i) => {
      ret[i] = x
      x += column.width
    })
    return ret
  }, [columns])

  const refresh = React.useCallback(() => {
    if (viewport === null || tbody === null) {
      return // a race? [adamhooper, 2020-11-11] dunno if this can ever be reached
    }
    const thMeasurements = getRowThMeasurementsFromTbody(tbody)
    if (thMeasurements === null) {
      return
    }
    const { thWidth, rowHeight } = thMeasurements
    const headerHeight = tbody.offsetTop

    const x0 = viewport.scrollLeft
    const x1 = x0 + Math.max(0, viewport.clientWidth - thWidth)
    const y0 = viewport.scrollTop
    const y1 = y0 + Math.max(0, viewport.clientHeight - headerHeight)

    const r0 = Math.floor(y0 / rowHeight)
    const r1 = Math.min(Math.ceil(y1 / rowHeight), nRows)
    let c0 = 0
    let c1 = columnOffsetsAfterTh.length
    for (let i = 0; i < columnOffsetsAfterTh.length; i++) {
      if (columnOffsetsAfterTh[i] < x0) {
        c0 = i
      }
      if (columnOffsetsAfterTh[i] > x1) {
        c1 = i
        break
      }
    }

    setFocusCellRange(r0, r1, c0, c1)
  }, [
    viewport,
    focusCell,
    tbody,
    nRows,
    JSON.stringify(columnOffsetsAfterTh) /* array-compare */,
    setFocusCellRange
  ])
  const throttledRefresh = useThrottledRequestAnimationFrame(refresh)

  React.useLayoutEffect(() => {
    if (viewport !== null && tbody !== null) {
      // Call setFocusCellRange() ... and schedule it to happen when anything resizes
      refresh()

      const resizeObserver = new global.ResizeObserver(throttledRefresh)
      resizeObserver.observe(viewport)
      resizeObserver.observe(tbody)

      return () => resizeObserver.disconnect()
    }
  }, [viewport, tbody, refresh, throttledRefresh])

  React.useLayoutEffect(() => {
    if (viewport !== null && tbody !== null && focusCell && focusCell.row !== null) {
      const thMeasurements = getRowThMeasurementsFromTbody(tbody)
      if (thMeasurements === null) {
        return
      }
      const { thWidth, rowHeight } = thMeasurements
      const headerHeight = tbody.offsetTop

      // All these coords are relative to the top-left of the first <td> in the <tbody>.
      // Its position is x=thWidth, y=tbody.offsetTop

      const cellX0 = focusCell.column === null
        ? null
        : columns.slice(0, focusCell.column).reduce((acc, col) => acc + col.width, 0)
      const cellX1 = focusCell.column === null
        ? null
        : cellX0 + columns[focusCell.column].width
      const cellY0 = focusCell.row * rowHeight
      const cellY1 = cellY0 + rowHeight

      const x0 = viewport.scrollLeft
      const x1 = x0 + viewport.clientWidth - thWidth
      const y0 = viewport.scrollTop
      const y1 = y0 + viewport.clientHeight - headerHeight

      const margin = 2

      if (cellY0 < y0 || cellY1 > y1 || (cellX0 !== null && cellX0 < x0) || (cellX1 !== null && cellX1 > x1)) {
        if (cellY0 < y0) {
          viewport.scrollTop = Math.max(0, cellY0 - margin)
        }
        if (cellY1 > y1) {
          viewport.scrollTop = Math.max(0, cellY1 - viewport.clientHeight + headerHeight + margin)
        }
        if (cellX0 !== null && cellX0 < x0) {
          viewport.scrollLeft = Math.max(0, cellX0 - margin)
        }
        if (cellX1 !== null && cellX1 > x1) {
          viewport.scrollLeft = Math.max(0, cellX1 - viewport.clientWidth + thWidth + margin)
        }
      }
    }
  }, [viewport, tbody, focusCell, columns])

  return (
    <div
      className='big-table'
      onScroll={throttledRefresh /* calls setFocusCellRange() */}
      ref={setViewport}
    >
      <Table
        nRows={nRows}
        columns={columns}
        nSkipRows={nSkipRows}
        nSkipColumns={nSkipColumns}
        cells={cells}
        tbodyRef={setTbody}
        onEdit={onEdit}
      />
    </div>
  )
}
Viewport.propTypes = {
  nRows: PropTypes.number.isRequired,
  columns: PropTypes.array.isRequired,
  nSkipRows: PropTypes.number.isRequired,
  nSkipColumns: PropTypes.number.isRequired,
  cells: PropTypes.arrayOf(
    PropTypes.arrayOf(
      PropTypes.oneOfType([
        // JSON data values the server can send us
        PropTypes.number.isRequired,
        PropTypes.string.isRequired
      ]) // or null
    ).isRequired
  ).isRequired,
  setFocusCellRange: PropTypes.func.isRequired,
  onEdit: PropTypes.func // func({ row, column, oldValue, newValue }) => undefined, or null
}
