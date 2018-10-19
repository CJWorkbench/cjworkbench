// ---- TableView ----
// Displays a module's rendered output, if any
// Handles paged loading of data, which also means it decides when to turn the OutputPane spinner on

import React from 'react'
import PropTypes from 'prop-types'
import DataGrid from './DataGrid'
import TableInfo from './TableInfo'
import * as UpdateTableAction from './UpdateTableAction'

export const NMaxColumns = 100

export default class TableView extends React.PureComponent {
  static propTypes = {
    api: PropTypes.object.isRequired,
    wfModuleId: PropTypes.number, // immutable; null for placeholder table
    deltaId: PropTypes.number, // immutable; null for placeholder table
    columns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    }).isRequired), // immutable; null for placeholder table
    nRows: PropTypes.number, // immutable; null for placeholder table
    api: PropTypes.object.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onLoadPage: PropTypes.func.isRequired, // func(wfModuleId, deltaId) => undefined
    showColumnLetter: PropTypes.bool.isRequired
  }

  // componentDidMount will trigger first load
  state = {
    selectedRowIndexes: [],
  }

  setSelectedRowIndexes = (selectedRowIndexes) => {
    this.setState({ selectedRowIndexes })
  }

  // When a cell is edited we need to 1) update our own state 2) add this edit to an Edit Cells module
  onEditCell = (rowIndex, colName, newVal) => {
    // Add an edit if the data has actually changed. Cast everything to string for comparisons.
    UpdateTableAction.updateTableActionModule(this.props.wfModuleId, 'editcells', false, {row: rowIndex, col: colName, value: newVal})
  }

  onSelectColumns = () => {
    UpdateTableAction.updateTableActionModule(this.props.wfModuleId,
      'selectcolumns', false, {columnKey: '', keep: true})
  }

  setDropdownAction = (idName, forceNewModule, params) => {
    UpdateTableAction.updateTableActionModule(this.props.wfModuleId, idName, forceNewModule, params)
  }

  render() {
    // Make a table component if we have the data
    const { selectedRowIndexes } = this.state
    const { api, wfModuleId, deltaId, isReadOnly, columns, nRows, showColumnLetter, onLoadPage } = this.props
    const tooWide = columns.length > NMaxColumns

    let gridView
    if (tooWide) {
      // TODO nix all the <div>s
      gridView = (
        <div className="overlay">
          <div>
            <div className="text">
              A maximum of 100 columns can be displayed
            </div>
            <button className="add-select-module" onClick={this.onSelectColumns}>Select columns</button>
          </div>
        </div>
      )
    } else {
      gridView = (
        <DataGrid
          api={api}
          isReadOnly={isReadOnly}
          wfModuleId={wfModuleId}
          deltaId={deltaId}
          columns={columns}
          nRows={nRows}
          onEditCell={this.onEditCell}
          showLetter={showColumnLetter}
          onReorderColumns={UpdateTableAction.updateTableActionModule}
          onRenameColumn={UpdateTableAction.updateTableActionModule}
          isReadOnly={isReadOnly}
          setDropdownAction={this.setDropdownAction}
          selectedRowIndexes={selectedRowIndexes}
          onLoadPage={onLoadPage}
          onSetSelectedRowIndexes={this.setSelectedRowIndexes}
          key={wfModuleId + '-' + deltaId}
        />
      )
    }

    return (
      <div className="outputpane-table">
        <TableInfo
          isReadOnly={isReadOnly}
          wfModuleId={wfModuleId}
          nRows={wfModuleId ? nRows : null}
          nColumns={(wfModuleId && columns) ? columns.length : null}
          selectedRowIndexes={selectedRowIndexes}
        />
        <div className="outputpane-data">
          {gridView}
        </div>
      </div>
    )
  }
}
