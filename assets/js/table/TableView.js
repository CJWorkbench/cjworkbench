import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../propTypes'
import DataGrid from './DataGrid'
import TableInfo from './TableInfo'
import { FocusCellProvider, RowSelectionProvider } from '../BigTable/state'
import { connect } from 'react-redux'
import { updateTableAction } from './UpdateTableAction'

export function TableView (props) {
  const {
    workflowIdOrSecretId,
    stepSlug,
    stepId,
    deltaId,
    isReadOnly,
    columns,
    nRows,
    nRowsPerTile,
    nColumnsPerTile,
    onTableLoaded,
    editCell
  } = props

  const handleEdit = React.useMemo(() => {
    if (isReadOnly) return null
    return ({ row, column, newValue }) => {
      editCell(stepId, row, columns[column].name, newValue)
    }
  }, [columns, editCell, stepId, isReadOnly])

  // const reorderColumn = (column, fromIndex, toIndex) => {
  //   this.props.reorderColumn(this.props.stepId, column, fromIndex, toIndex)
  // }

  return (
    <FocusCellProvider>
      <RowSelectionProvider>
        <div className='outputpane-table'>
          <TableInfo
            isReadOnly={isReadOnly}
            workflowIdOrSecretId={workflowIdOrSecretId}
            stepId={stepId}
            stepSlug={stepSlug}
            nRows={stepSlug ? nRows : null}
            nColumns={stepSlug && columns ? columns.length : null}
          />
          <div className='outputpane-data'>
            <DataGrid
              workflowIdOrSecretId={workflowIdOrSecretId}
              stepSlug={stepSlug}
              stepId={stepId}
              deltaId={deltaId}
              nRows={nRows}
              columns={columns}
              nRowsPerTile={nRowsPerTile}
              nColumnsPerTile={nColumnsPerTile}
              onTableLoaded={onTableLoaded}
              isReadOnly={isReadOnly}
              onEdit={handleEdit}
            />
          </div>
        </div>
      </RowSelectionProvider>
    </FocusCellProvider>
  )
}
TableView.propTypes = {
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  stepSlug: PropTypes.string, // null for placeholder table
  stepId: PropTypes.number, // immutable; null for placeholder table; deprecated
  deltaId: PropTypes.number, // immutable; null for placeholder table
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['date', 'text', 'number', 'timestamp']).isRequired
    }).isRequired
  ), // immutable; null for placeholder table
  nRows: PropTypes.number, // immutable; null for placeholder table
  isReadOnly: PropTypes.bool.isRequired,
  onTableLoaded: PropTypes.func, // func({ stepSlug, deltaId }) => undefined
  ensureSelectColumnsModule: PropTypes.func.isRequired, // func(stepId) => undefined
  reorderColumn: PropTypes.func.isRequired // func(stepId, colname, fromIndex, toIndex) => undefined
}

function mapStateToProps (state) {
  return {
    nColumnsPerTile: state.settings.bigTableColumnsPerTile,
    nRowsPerTile: state.settings.bigTableRowsPerTile
  }
}

function mapDispatchToProps (dispatch) {
  return {
    ensureSelectColumnsModule: stepId => {
      dispatch(updateTableAction(stepId, 'selectcolumns', false, {}))
    },
    reorderColumn: (stepId, colname, fromIndex, toIndex) => {
      dispatch(
        updateTableAction(stepId, 'reordercolumns', false, {
          column: colname,
          from: fromIndex,
          to: toIndex
        })
      )
    },
    editCell: (stepId, rowIndex, colname, newValue) => {
      dispatch(
        updateTableAction(stepId, 'editcells', false, {
          row: rowIndex,
          col: colname,
          value: newValue
        })
      )
    }
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(TableView)
