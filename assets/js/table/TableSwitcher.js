import React from 'react'
import PropTypes from 'prop-types'
import Spinner from '../Spinner'
import TableView from './TableView'

// NoStepTable: shown when no Step is selected
// Do not render zero-row tables: render a placeholder instead
// Helps #161166382, hinders #160865813
const NoStepTableColumns = [
  { name: ' ', type: 'text' },
  { name: '  ', type: 'text' },
  { name: '   ', type: 'text' },
  { name: '    ', type: 'text' }
]
const NoStepLoadRows = () => Promise.resolve([{}, {}, {}, {}, {}, {}, {}, {}, {}, {}])
const NoStepTable = () => (
  <TableView
    loadRows={NoStepLoadRows}
    isReadOnly
    stepId={null}
    deltaId={null}
    columns={NoStepTableColumns}
    nRows={10}
  />
)

// BusyStepTable: shown when Step render() has not yet been called
const BusyStepTable = () => (
  <Spinner />
)

// UnreachableStepTable: shown when selected Step comes after an error
const UnreachableStepTable = () => (
  <TableView
    isReadOnly
    stepId={null}
    deltaId={null}
    columns={NoStepTableColumns}
    loadRows={NoStepLoadRows}
    nRows={10}
  />
)

const OkStepTable = React.memo(function OkStepTable ({ isLoaded, isReadOnly, stepId, deltaId, columns, nRows, loadRows }) {
  return (
    <>
      <TableView
        isReadOnly={isReadOnly}
        loadRows={loadRows}
        stepId={stepId}
        deltaId={deltaId}
        columns={columns}
        nRows={nRows}
      />
      {isLoaded ? null : <Spinner />}
    </>
  )
})

const TableSwitcherContents = React.memo(function TableSwitcherContents ({ status, nRows, ...props }) {
  if (status === null) {
    return <NoStepTable />
  } else if (status === 'busy') {
    return <BusyStepTable />
  } else if (status === 'unreachable') {
    return <UnreachableStepTable />
  } else {
    return <OkStepTable nRows={nRows} {...props} />
  }
})

/**
 * Displays the given table, with its status in mind.
 *
 * Depending on input, the table may be:
 *
 * * NoStepTable: shown when there is no selection.
 * * BusyStepTable: shown when the step is busy (a Spinner).
 * * UnreachableStepTable: shown when the step is unreachable.
 * * OkStepTable: shown when table data is available.
 *
 * There is no ErrorStepTable, because we never show an Error-status step. (We
 * show its input.)
 */
export default class TableSwitcher extends React.PureComponent {
  static propTypes = {
    loadRows: PropTypes.func.isRequired, // func(stepId, deltaId, startRowInclusive, endRowExclusive) => Promise[Array[Object] or error]
    isLoaded: PropTypes.bool.isRequired, // true unless we haven't loaded any data at all yet
    isReadOnly: PropTypes.bool.isRequired,
    stepId: PropTypes.number, // or null, if no selection
    deltaId: PropTypes.number, // or null, if status!=ok
    status: PropTypes.oneOf(['ok', 'busy', 'unreachable']), // null if no selection
    columns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'timestamp', 'number']).isRequired
    }).isRequired), // or null, if status!=ok
    nRows: PropTypes.number // or null, if status!=ok
  }

  render () {
    const { isLoaded } = this.props
    return (
      <div className={`${isLoaded ? 'loaded-table' : 'loading-table'}`}>
        <TableSwitcherContents {...this.props} />
      </div>
    )
  }
}
