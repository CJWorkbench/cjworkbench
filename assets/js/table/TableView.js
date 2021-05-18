import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../propTypes'
import DataGrid from './DataGrid'
import TableInfo from './TableInfo'
import {
  FocusCellContext,
  FocusCellSetterContext,
  RowSelectionContext,
  RowSelectionSetterContext
} from '../BigTable/state'
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
    onTableLoaded
  } = props

  const [focusCell, setFocusCell] = React.useState({ row: null, column: null })
  const [rowSelection, setRowSelection] = React.useState(new Uint8Array())

  // When a cell is edited we need to 1) update our own state 2) add this edit to an Edit Cells module
  // const editCell = (rowIndex, colname, newValue) => {
  //   this.props.editCell(this.props.stepId, rowIndex, colname, newValue)
  // }

  // const reorderColumn = (column, fromIndex, toIndex) => {
  //   this.props.reorderColumn(this.props.stepId, column, fromIndex, toIndex)
  // }

  return (
    <FocusCellContext.Provider value={focusCell}>
      <FocusCellSetterContext.Provider value={setFocusCell}>
        <RowSelectionContext.Provider value={rowSelection}>
          <RowSelectionSetterContext.Provider value={setRowSelection}>
            <div className='outputpane-table'>
              <TableInfo
                isReadOnly={isReadOnly}
                workflowIdOrSecretId={workflowIdOrSecretId}
                stepId={stepId}
                stepSlug={stepSlug}
                nRows={stepSlug ? nRows : null}
                nColumns={stepSlug && columns ? columns.length : null}
                rowSelection={rowSelection.slice(0, nRows || 0)}
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
                />
              </div>
            </div>
          </RowSelectionSetterContext.Provider>
        </RowSelectionContext.Provider>
      </FocusCellSetterContext.Provider>
    </FocusCellContext.Provider>
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
