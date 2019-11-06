// ---- TableView ----
// Displays a module's rendered output, if any
// Handles paged loading of data, which also means it decides when to turn the OutputPane spinner on

import React from 'react'
import PropTypes from 'prop-types'
import DataGrid from './DataGrid'
import TableInfo from './TableInfo'
import { connect } from 'react-redux'
import { updateTableAction } from './UpdateTableAction'
import { Trans } from '@lingui/macro'

export const NMaxColumns = 100

export class TableView extends React.PureComponent {
  static propTypes = {
    loadRows: PropTypes.func.isRequired, // func(wfModuleId, deltaId, startRowInclusive, endRowExclusive) => Promise[Array[Object] or error]
    wfModuleId: PropTypes.number, // immutable; null for placeholder table
    deltaId: PropTypes.number, // immutable; null for placeholder table
    columns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    }).isRequired), // immutable; null for placeholder table
    nRows: PropTypes.number, // immutable; null for placeholder table
    isReadOnly: PropTypes.bool.isRequired,
    ensureSelectColumnsModule: PropTypes.func.isRequired, // func(wfModuleId) => undefined
    reorderColumn: PropTypes.func.isRequired // func(wfModuleId, colname, fromIndex, toIndex) => undefined
  }

  // componentDidMount will trigger first load
  state = {
    selectedRowIndexes: []
  }

  handleSetSelectedRowIndexes = (selectedRowIndexes) => {
    this.setState({ selectedRowIndexes })
  }

  // When a cell is edited we need to 1) update our own state 2) add this edit to an Edit Cells module
  editCell = (rowIndex, colname, newValue) => {
    this.props.editCell(this.props.wfModuleId, rowIndex, colname, newValue)
  }

  handleClickSelectColumns = () => {
    this.props.ensureSelectColumnsModule(this.props.wfModuleId)
  }

  reorderColumn = (column, fromIndex, toIndex) => {
    this.props.reorderColumn(this.props.wfModuleId, column, fromIndex, toIndex)
  }

  render () {
    // Make a table component if we have the data
    const { selectedRowIndexes } = this.state
    const { loadRows, wfModuleId, deltaId, isReadOnly, columns, nRows } = this.props
    const tooWide = columns.length > NMaxColumns

    let gridView
    if (tooWide) {
      // TODO nix all the <div>s
      gridView = (
        <div className='overlay'>
          <div>
            <div className='text'>
              <Trans id='js.table.TableView.maxOf100ColumnsCanbeDIsplayed'>A maximum of 100 columns can be displayed</Trans>
            </div>
            <button className='add-select-module' onClick={this.handleClickSelectColumns}><Trans id='js.table.TableView.selectColumns.button'>Select columns</Trans></button>
          </div>
        </div>
      )
    } else {
      gridView = (
        <DataGrid
          loadRows={loadRows}
          isReadOnly={isReadOnly}
          wfModuleId={wfModuleId}
          deltaId={deltaId}
          columns={columns}
          nRows={nRows}
          editCell={this.editCell}
          reorderColumn={this.reorderColumn}
          selectedRowIndexes={selectedRowIndexes}
          onSetSelectedRowIndexes={this.handleSetSelectedRowIndexes}
          key={wfModuleId + '-' + deltaId}
        />
      )
    }

    return (
      <div className='outputpane-table'>
        <TableInfo
          isReadOnly={isReadOnly}
          wfModuleId={wfModuleId}
          nRows={wfModuleId ? nRows : null}
          nColumns={(wfModuleId && columns) ? columns.length : null}
          selectedRowIndexes={selectedRowIndexes}
        />
        <div className='outputpane-data'>
          {gridView}
        </div>
      </div>
    )
  }
}

function mapDispatchToProps (dispatch) {
  return {
    ensureSelectColumnsModule: (wfModuleId) => {
      dispatch(updateTableAction(wfModuleId, 'selectcolumns', false, {}))
    },
    reorderColumn: (wfModuleId, colname, fromIndex, toIndex) => {
      dispatch(updateTableAction(wfModuleId, 'reordercolumns', false, {
        column: colname,
        from: fromIndex,
        to: toIndex
      }))
    },
    editCell: (wfModuleId, rowIndex, colname, newValue) => {
      dispatch(updateTableAction(wfModuleId, 'editcells', false, {
        row: rowIndex,
        col: colname,
        value: newValue
      }))
    }
  }
}

export default connect(null, mapDispatchToProps)(TableView)
