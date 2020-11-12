import React from 'react'
import PropTypes from 'prop-types'
import useThrottledRequestAnimationFrame from './useThrottledRequestAnimationFrame'
import Table from './Table'

export default function Viewport ({ nRows, columns, cells, nSkipRows, nSkipColumns, setFocusCellRange }) {
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
    const cell1 = tbody.querySelector('tr:not(.updating)>th')
    if (!cell1) {
      // We must be redrawing? There should _always_ be a focal range, because
      // we started with non-empty (see useFocalCells.js) and there's no way to
      // revert to non-empty.
      return
    }
    const cell1Rect = cell1.getBoundingClientRect()
    const thWidth = cell1Rect.width
    const rowHeight = cell1Rect.height / cell1.rowSpan
    const headerHeight = tbody.offsetTop

    const x0 = viewport.scrollLeft
    const x1 = x0 + viewport.offsetWidth - thWidth
    const y0 = viewport.scrollTop
    const y1 = y0 + viewport.offsetHeight - headerHeight

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
  }, [viewport, tbody, nRows, JSON.stringify(columnOffsetsAfterTh) /* array-compare */, setFocusCellRange])
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
  setFocusCellRange: PropTypes.func.isRequired
}
