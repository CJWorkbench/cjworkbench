import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../propTypes'
import TableSwitcher from './TableSwitcher'
import Spinner from '../Spinner'

/**
 * Given props, return the React "key".
 *
 * This forces React to re-render new tables and saves React from re-rendering
 * when switching from "loading" to "loaded".
 */
function tableKey ({ stepSlug, deltaId }) {
  return `table-${stepSlug}-${deltaId}`
}

/**
 * Shows a <TableSwitcher> for the given step+deltaId -- and transitions
 * when those props change.
 *
 * The transition is: this.state maintains a "last-loaded" step+deltaId.
 * When we switch to a new step+deltaId that has not yet loaded (or has
 * nRows===null), we keep that stale table visible atop the new, unloaded one
 * and we show a spinner.
 *
 *   <div className="table-switcher">
 *     <div className="loaded-table">
 *       <TableView ... /> <!-- last table we've seen with data -->
 *     </div>
 *     <div className="loading-table">
 *       <TableView ... /> <!-- next table -- when it loads, we'll move it -->
 *     </div>
 *   </div>
 *
 * this.state holds the _loaded_ table. this.props holds the _loading_ table.
 *
 * Behind the state, a table in `this.props` goes through two stages:
 *
 * 1. Loading. The old data should still be visible; the new table should
 *    display as a spinner.
 * 2. In `state.loaded`. That is, `state.loaded` is equivalent to `this.props`.
 *
 * We call the table in `this.props` the "current table". The table in state (if
 * any) is the "loaded table".
 */
export default function DelayedTableSwitcher (props) {
  const {
    isReadOnly,
    workflowIdOrSecretId,
    stepSlug,
    stepId,
    deltaId,
    status,
    columns,
    nRows
  } = props

  const [loadedTable, setLoadedTable] = React.useState(null)
  const currentTable = React.useMemo(
    () => ({
      isReadOnly,
      workflowIdOrSecretId,
      stepSlug,
      stepId,
      deltaId,
      status,
      columns,
      nRows
    }),
    [
      isReadOnly,
      workflowIdOrSecretId,
      stepSlug,
      stepId,
      deltaId,
      status,
      columns,
      nRows
    ]
  )

  const handleTableLoaded = React.useCallback(
    ({ stepSlug, deltaId }) => {
      if (tableKey(currentTable) === tableKey({ stepSlug, deltaId })) {
        setLoadedTable(currentTable)
      }
    },
    [setLoadedTable, currentTable]
  )

  let className = 'table-switcher'

  // Show the last table that has data visible (from state)
  //
  // If input props have stepId=null, that's a "loaded" table -- an
  // empty-looking one.
  if (loadedTable) className += ' has-loaded'

  // Show requested table afterwards -- styled differently (and on top)
  //
  // It's always the case that `!!loading || !!loaded`
  const loading = loadedTable === null || tableKey(loadedTable) !== tableKey(currentTable)
  if (loading) className += ' has-loading'

  const waiting = loading || currentTable.status === 'busy'

  React.useEffect(() => {
    if (
      (currentTable.status !== 'busy' && currentTable.stepSlug === null) || // empty tab is loaded table
      (currentTable.status !== 'busy' && currentTable.nRows === 0) // 0-row table is loaded table
    ) {
      setLoadedTable(currentTable)
    }
  }, [setLoadedTable, currentTable, loadedTable])

  // Notice the nifty optimization: we make sure React will not redraw a
  // table when switching from "loading" to "loaded": its `key` will remain
  // the same.
  return (
    <div className={className}>
      {loadedTable
        ? (
          <TableSwitcher
            {...loadedTable}
            isReadOnly={isReadOnly || loading}
            isLoaded
            key={tableKey(loadedTable)}
          />
          )
        : null}
      {loading
        ? (
          <TableSwitcher
            {...currentTable}
            isReadOnly
            isLoaded={false}
            key={tableKey(currentTable)}
            onTableLoaded={handleTableLoaded}
          />
          )
        : null}
      {waiting ? <Spinner /> : null}
    </div>
  )
}
DelayedTableSwitcher.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  stepSlug: PropTypes.string, // or null, if no selection
  stepId: PropTypes.number, // or null, if no selection; deprecated
  deltaId: PropTypes.number, // or null, if status!=ok
  status: PropTypes.oneOf(['ok', 'busy', 'unreachable']), // null if no selection
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['date', 'text', 'timestamp', 'number']).isRequired
    }).isRequired
  ), // or null, if status!=ok
  nRows: PropTypes.number // or null, if status!=ok
}
