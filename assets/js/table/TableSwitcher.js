import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../propTypes'
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
const NoStepTable = (props) => (
  <TableView
    isReadOnly
    workflowIdOrSecretId={props.workflowIdOrSecretId}
    stepSlug={null}
    stepId={null}
    deltaId={null}
    columns={NoStepTableColumns}
    nRows={10}
  />
)

// BusyStepTable: shown when Step render() has not yet been called
const BusyStepTable = () => <Spinner />

// UnreachableStepTable: shown when selected Step comes after an error
const UnreachableStepTable = NoStepTable

const OkStepTable = React.memo(function OkStepTable ({
  isLoaded,
  isReadOnly,
  workflowIdOrSecretId,
  stepSlug,
  stepId,
  deltaId,
  columns,
  nRows,
  onTableLoaded
}) {
  return (
    <TableView
      isReadOnly={isReadOnly}
      workflowIdOrSecretId={workflowIdOrSecretId}
      stepSlug={stepSlug}
      stepId={stepId}
      deltaId={deltaId}
      columns={columns}
      nRows={nRows}
      onTableLoaded={onTableLoaded}
    />
  )
})

const TableSwitcherContents = React.memo(function TableSwitcherContents ({
  status,
  nRows,
  ...props
}) {
  if (status === null) {
    return <NoStepTable workflowIdOrSecretId={props.workflowIdOrSecretId} />
  } else if (status === 'busy') {
    return <BusyStepTable workflowIdOrSecretId={props.workflowIdOrSecretId} />
  } else if (status === 'unreachable') {
    return <UnreachableStepTable workflowIdOrSecretId={props.workflowIdOrSecretId} />
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
    isLoaded: PropTypes.bool.isRequired, // true unless we haven't loaded any data at all yet
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
    nRows: PropTypes.number, // or null, if status!=ok
    onTableLoaded: PropTypes.func // func({ stepSlug, deltaId }) => undefined
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
