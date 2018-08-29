// ---- TableView ----
// Displays a module's rendered output, if any
// Handles paged loading of data, which also means it decides when to turn the OutputPane spinner on

import React from 'react'
import PropTypes from 'prop-types'
import DataGrid from './DataGrid'
import ExportModal from "./ExportModal"
import update from 'immutability-helper'
import * as UpdateTableAction from './UpdateTableAction'
import { findParamValByIdName } from './utils'

export const NRowsPerPage = 200 // exported to help tests
export const FetchTimeout = 50 // ms after scroll before fetch

const NumberFormat = new Intl.NumberFormat('en-US')

// We'll cache some data on TableView that isn't props or state.
const InitialValues = {
  minMissingRowIndex: null,
  maxMissingRowIndex: null,
  scheduleLoadTimeout: null,
  emptyRow: { '': '', ' ': '', '  ': '', '   ': '' }
}

const InitialState = {
  loadedRows: [],
  columns: null,
  columnTypes: null,
  totalNRows: null,
  loading: false,
  wasJustReset: false
}

export default class TableView extends React.PureComponent {
  static propTypes = {
    selectedWfModuleId: PropTypes.number,             // not actually required, could have no selected module
    lastRelevantDeltaId: PropTypes.number.isRequired,
    api: PropTypes.object.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    setBusySpinner: PropTypes.func,
    showColumnLetter: PropTypes.bool.isRequired,
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number,
  }

  constructor(props) {
    super(props)

    // componentDidMount will trigger first load
    this.state = Object.assign({
      isExportModalOpen: false,
    }, InitialState)

    // Missing row indexes: every call to getRow() we might set these and run
    // this.scheduleLoad().
    //
    // They aren't in this.state because editing them shouldn't cause re-render
    Object.assign(this, InitialValues)

    this.setDropdownAction = this.setDropdownAction.bind(this)
  }

  scheduleLoad () {
    if (this.scheduleLoadTimeout === null) {
      this.scheduleLoadTimeout = window.setTimeout(() => this.load(), FetchTimeout)
    }
  }

  componentWillUnmount () {
    this.reset() // cancel timeout
    this.unmounted = true
  }

  /**
   * Mark the table as needing reloading.
   *
   * For a fluid UX, we want to leave the existing table in place while
   * loading new data.
   *
   * This will trigger render(), which will eventually call getRow(), which
   * will trigger load. (You may load() before that, if you prefer.)
   */
  reset () {
    if (this.scheduleLoadTimeout !== null) {
      window.clearTimeout(this.scheduleLoadTimeout)
    }
    // Leave old values in this.state, so we keep rendering them until new
    // values are loaded.
  }

  load (wasJustReset=false) {
    const min = this.minMissingRowIndex
    const max = min + NRowsPerPage // don't care about maxMissingRowIndex...
    const wfModuleId = this.props.selectedWfModuleId
    const { lastRelevantDeltaId } = this.props
    const { loadedRows } = this.state

    this.minMissingRowIndex = null
    this.maxMissingRowIndex = null
    this.scheduleLoadTimeout = null

    let areAllValuesMissing = !wasJustReset
    for (let i = min; i < max; i++) {
      if (loadedRows[i]) {
        areAllValuesMissing = false
        break
      }
    }
    if (areAllValuesMissing) {
      this.setBusySpinner(true)
    }

    this.setState({ loading: true })
    this.props.api.render(this.props.selectedWfModuleId, min, max + 1) // +1: of-by-one oddness in API
      .then(json => {
        // Avoid races: return if we've changed what we want to fetch
        if (wfModuleId !== this.props.selectedWfModuleId) return
        if (lastRelevantDeltaId !== this.props.lastRelevantDeltaId) return
        if (json.start_row !== min) return
        if (this.unmounted) return

        const loadedRows = wasJustReset ? [] : this.state.loadedRows.slice()
        const totalNRows = json.total_rows
        const columns = (!wasJustReset && this.state.columns) || json.columns
        const columnTypes = (!wasJustReset && this.state.columnTypes) || json.column_types

        // expand the Array (filling undefined for missing values in between)
        loadedRows[json.start_row] = null
        // add the new rows
        loadedRows.splice(json.start_row, json.rows.length, ...json.rows)

        this.setState({
          loading: false,
          totalNRows,
          loadedRows,
          columns,
          columnTypes,
          wasJustReset: false
        })

        this.setBusySpinner(false)
      })
  }

  openExportModal = () => {
    this.setState({ isExportModalOpen: true })
  }

  closeExportModal = () => {
    this.setState({ isExportModalOpen: false })
  }

  // safe wrapper as setBusySpinner prop is optional
  setBusySpinner(visible) {
    if (this.props.setBusySpinner)
      this.props.setBusySpinner(visible);
  }

  // Completely reload table data -- puts up spinner, preserves visibility of old data while we wait
  refreshTable() {
    if (this.props.selectedWfModuleId) {
      this.setBusySpinner(true)

      this.reset()
      this.minMissingRowIndex = 0
      this.maxMissingRowIndex = NRowsPerPage

      // Set this.state.loading=true and begin the fetch
      // we know scheduleLoadTimeout is null because reset() reset it
      this.load(true)
    }
  }

  // Load more table data from render API. Spinner if we're going to see blanks.
  loadTable(toRow) {
    if (this.props.selectedWfModuleId) {
      this.loading = true;

      // Spinner if we've used up all our preloaded rows (we're now seeing blanks)
      if (toRow >= this.state.lastLoadedRow + preloadRows + deltaRows) {
        this.setBusySpinner(true);
      }

      this.props.api.render(this.props.selectedWfModuleId, this.state.lastLoadedRow, toRow)
        .then(json => {

          // Add just retrieved rows to current data, if any
          if (this.state.tableData) {
            json.rows = this.state.tableData.rows.concat(json.rows);
            json.start_row = 0;  // no one looks at this currently, but they might
          }

          this.emptyRow = json.columns.reduce((obj, col) => { obj[col] = null; return obj }, {})

          this.loading = false;
          this.setBusySpinner(false);
          this.setState({
            tableData: json,
          });
        });
    }
  }

  componentDidMount () {
    this.refreshTable()  // refresh, not load, so we get the spinner
  }

  // If the lastRelevantDeltaId changes from under us, or we are displaying a different output, reload the table
  componentDidUpdate (prevProps) {
    if (this.props.lastRelevantDeltaId !== prevProps.lastRelevantDeltaId || this.props.selectedWfModuleId !== prevProps.selectedWfModuleId) {
      this.refreshTable();
    }
  }

  getRow = (i) => {
    const { loadedRows, loading } = this.state

    if (loadedRows[i]) {
      this.renderedAtLeastOneNonEmptyRow = true
      return loadedRows[i]
    } else {
      if (!loading) {
        // Queue load for when we have time
        this.minMissingRowIndex = Math.min(i, this.minMissingRowIndex || i)
        this.maxMissingRowIndex = Math.max(i, this.maxMissingRowIndex || i)
        this.scheduleLoad()
      } else {
        // no-op: there will be another render after the load finishes, and
        // after _that_ we can start our fetching.
      }

      // Return something right now, in the meantime
      return this.emptyRow
    }
  }

  // When a cell is edited we need to 1) update our own state 2) add this edit to an Edit Cells module
  onEditCell = (rowIndex, colName, newVal) => {
    const row = this.state.loadedRows[rowIndex]
    if (!row) return // should never happen

    // Add an edit if the data has actually changed. Cast everything to string for comparisons.
    const oldVal = row[colName]
    if (newVal !== (oldVal || '')) {
      // Change just this one row
      const newRow = Object.assign({}, row, { [colName]: newVal })
      const loadedRows = this.state.loadedRows.slice()
      loadedRows[rowIndex] = newRow
      this.setState({ loadedRows })

      UpdateTableAction.updateTableActionModule(this.props.selectedWfModuleId, 'editcells', false, {row: rowIndex, col: colName, value: newVal})
    }
  }

  setDropdownAction (idName, forceNewModule, params) {
    UpdateTableAction.updateTableActionModule(this.props.selectedWfModuleId, idName, forceNewModule, params);
      this.refreshTable();
  }

  render() {
    // Make a table component if we have the data
    let nRowsString
    let nColsString
    let gridView

    if (this.props.selectedWfModuleId && this.state.totalNRows > 0) {
      const { sortColumn, sortDirection, showColumnLetter } = this.props

      // DataGrid is the heaviest DOM tree we have, and it effects the
      // performance of the custom drag layer (and probably everything else). By
      // putting a no-op translate3d property on it, we coerce browsers into
      // rendering it and all of its children in a seperate compositing layer,
      // improving the rendering of everything else in the app.
      gridView = (
        <div className="outputpane-data" style={{transform:'translate3d(0, 0, 0)'}}>
          <DataGrid
            totalRows={this.state.totalNRows}
            columns={this.state.columns}
            columnTypes={this.state.columnTypes}
            wfModuleId={this.props.selectedWfModuleId}
            lastRelevantDeltaId={this.props.lastRelevantDeltaId}
            getRow={this.getRow}
            onEditCell={this.onEditCell}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            showLetter={showColumnLetter}
            onReorderColumns={UpdateTableAction.updateTableActionModule}
            onRenameColumn={UpdateTableAction.updateTableActionModule}
            isReadOnly={this.props.isReadOnly}
            setDropdownAction={this.setDropdownAction}
          />
        </div>
      )
      nRowsString = NumberFormat.format(this.state.totalNRows)
      nColsString = NumberFormat.format(this.state.columns.length)
    } else {
      // Empty grid, big enough to fill screen.
      // 10 rows by four blank columns (each with a different number of spaces, for unique names)
      gridView = (
        <div className="outputpane-data">
          <DataGrid
            id={undefined}
            totalRows={10}
            columns={['',' ','   ','    ']}
            getRow={() => {return {}}}
            isReadOnly={this.props.isReadOnly}
            setDropdownAction={this.setDropdownAction}
            onRenameColumn={() => null}
            onReorderColumns={() => null}
          />
        </div>
      )
      nRowsString = ''
      nColsString = ''
    }

    return (
      <div className="outputpane-table">
          <div className="outputpane-header">
            <div className="table-info-container">
              <div className='table-info'>
                  <div className='data'>Rows</div>
                  <div className='value'>{nRowsString}</div>
              </div>
              <div className='table-info'>
                  <div className='data'>Columns</div>
                  <div className='value'>{nColsString}</div>
              </div>
            </div>
            {this.props.selectedWfModuleId ? (
              <div className="export-table" onClick={this.openExportModal}>
                <i className="icon-download"></i>
                <span>CSV</span>
                <span className="feed">JSON FEED</span>
                <ExportModal
                  open={this.state.isExportModalOpen}
                  wfModuleId={this.props.selectedWfModuleId}
                  onClose={this.closeExportModal}
                />
              </div>
            ) : null}
          </div>
          {gridView}
      </div>
    )
  }
}
