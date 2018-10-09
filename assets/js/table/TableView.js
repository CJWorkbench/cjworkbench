// ---- TableView ----
// Displays a module's rendered output, if any
// Handles paged loading of data, which also means it decides when to turn the OutputPane spinner on

import React from 'react'
import PropTypes from 'prop-types'
import DataGrid from './DataGrid'
import TableInfo from './TableInfo'
import * as UpdateTableAction from './UpdateTableAction'

export const NRowsPerPage = 200 // exported to help tests
export const NMaxColumns = 100
export const FetchTimeout = 50 // ms after scroll before fetch

export default class TableView extends React.PureComponent {
  static propTypes = {
    wfModuleId: PropTypes.number, // null means no selected module
    deltaId: PropTypes.number, // or null
    columns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    }).isRequired), // or null
    nRows: PropTypes.number, // or null
    api: PropTypes.object.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    showColumnLetter: PropTypes.bool.isRequired,
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number
  }

  // componentDidMount will trigger first load
  state = {
    selectedRowIndexes: [],
    loadedRows: [],
    spinning: false // not "loading": we often load in bg, without an indicator
  }

  // We'll cache some data on TableView that isn't props or state.
  //
  // Quick refresher: `this.loading` is synchornous; `this.state.loading` is
  // async. In the example
  // `this.setState({ loading: true }); console.log(this.state.loading)`,
  // `console.log` will be called with the _previous_ value of
  // `this.state.loading`, which is not necessarily `true`. That's useless to
  // us. Only fill this.state with stuff we want to render.
  loading = false
  minMissingRowIndex = null
  maxMissingRowIndex = null
  scheduleLoadTimeout = null
  // Missing row indexes: every call to getRow() we might set these and run
  // this.scheduleLoad().
  emptyRow = { '': '', ' ': '', '  ': '', '   ': '' }

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
    const { deltaId, wfModuleId } = this.props
    const { loadedRows } = this.state

    this.minMissingRowIndex = null
    this.maxMissingRowIndex = null
    this.scheduleLoadTimeout = null

    if (wasJustReset) {
      this.setState({ selectedRowIndexes: [] })
    }

    let areAllValuesMissing = !wasJustReset
    for (let i = min; i < max; i++) {
      if (loadedRows[i]) {
        areAllValuesMissing = false
        break
      }
    }
    if (areAllValuesMissing) {
      this.setState({ spinning: true })
    }

    this.loading = true
    this.props.api.render(this.props.wfModuleId, min, max + 1) // +1: of-by-one oddness in API
      .then(json => {
        // Avoid races: return if we've changed what we want to fetch
        if (wfModuleId !== this.props.wfModuleId) return
        if (deltaId !== this.props.deltaId) return
        if (json.start_row !== min) return
        if (this.unmounted) return

        const loadedRows = wasJustReset ? [] : this.state.loadedRows.slice()

        // expand the Array (filling undefined for missing values in between)
        loadedRows[json.start_row] = null
        // add the new rows
        loadedRows.splice(json.start_row, json.rows.length, ...json.rows)

        this.loading = false
        this.setState({
          loadedRows,
          spinning: false
        })
      })
  }

  // Completely reload table data -- puts up spinner, preserves visibility of old data while we wait
  refreshTable() {
    if (this.props.wfModuleId) {
      this.setState({ spinning: true })

      this.reset()
      this.minMissingRowIndex = 0
      this.maxMissingRowIndex = NRowsPerPage

      // Set this.loading=true and begin the fetch
      // we know scheduleLoadTimeout is null because reset() reset it
      this.load(true)
    }
  }

  // Load more table data from render API. Spinner if we're going to see blanks.
  loadTable (toRow) {
    if (this.props.wfModuleId) {
      this.loading = true

      // Spinner if we've used up all our preloaded rows (we're now seeing blanks)
      if (toRow >= this.state.lastLoadedRow + preloadRows + deltaRows) {
        this.setState({ spinning: true })
      }

      this.props.api.render(this.props.wfModuleId, this.state.lastLoadedRow, toRow)
        .then(json => {

          // Add just retrieved rows to current data, if any
          if (this.state.tableData) {
            json.rows = this.state.tableData.rows.concat(json.rows);
            json.start_row = 0;  // no one looks at this currently, but they might
          }

          this.emptyRow = this.props.columns.reduce((obj, col) => { obj[col] = null; return obj }, {})

          this.loading = false
          this.setState({
            tableData: json,
            spinning: false
          })
        })
    }
  }

  setSelectedRowIndexes = (selectedRowIndexes) => {
    this.setState({ selectedRowIndexes })
  }

  componentDidMount () {
    this.refreshTable()  // refresh, not load, so we get the spinner
  }

  // If the deltaId changes from under us, or we are displaying a different output, reload the table
  componentDidUpdate (prevProps) {
    if (this.props.deltaId !== prevProps.deltaId || this.props.wfModuleId !== prevProps.wfModuleId) {
      this.refreshTable()
    }
  }

  getRow = (i) => {
    const { loadedRows } = this.state

    if (loadedRows[i]) {
      this.renderedAtLeastOneNonEmptyRow = true
      return loadedRows[i]
    } else {
      if (!this.loading) {
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

      UpdateTableAction.updateTableActionModule(this.props.wfModuleId, 'editcells', false, {row: rowIndex, col: colName, value: newVal})
    }
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
    const { spinning, selectedRowIndexes } = this.state
    const { wfModuleId, deltaId, isReadOnly, columns, nRows } = this.props
    const tooWide = (columns && columns.length > NMaxColumns)

    let gridView
    if (wfModuleId && nRows !== null && nRows !== 0 && !tooWide) {
      const { sortColumn, sortDirection, showColumnLetter } = this.props

      gridView = (
        <DataGrid
          wfModuleId={wfModuleId}
          deltaId={deltaId}
          columns={columns ? columns.map(c => c.name) : null}
          columnTypes={columns ? columns.map(c => c.type) : null}
          totalRows={nRows}
          getRow={this.getRow}
          onEditCell={this.onEditCell}
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          showLetter={showColumnLetter}
          onReorderColumns={UpdateTableAction.updateTableActionModule}
          onRenameColumn={UpdateTableAction.updateTableActionModule}
          isReadOnly={isReadOnly}
          setDropdownAction={this.setDropdownAction}
          selectedRowIndexes={selectedRowIndexes}
          onSetSelectedRowIndexes={this.setSelectedRowIndexes}
        />
      )
    } else {
      // Empty grid, big enough to fill screen.
      // 10 rows by four blank columns (each with a different number of spaces, for unique names)
      gridView = (
        <DataGrid
          id={undefined}
          columns={['',' ','   ','    ']}
          columnTypes={['text', 'text', 'text', 'text']}
          totalRows={10}
          getRow={() => {return {}}}
          isReadOnly={isReadOnly}
          setDropdownAction={this.setDropdownAction}
          selectedRowIndexes={selectedRowIndexes}
          onSetSelectedRowIndexes={() => null}
          onRenameColumn={() => null}
          onReorderColumns={() => null}
        />
      )
    }

    const maybeSpinner = !spinning ? null : (
      <div id="spinner-container-transparent">
        <div id="spinner-l1">
          <div id="spinner-l2">
            <div id="spinner-l3"></div>
          </div>
        </div>
      </div>
    )
    const maybeOverlay = !tooWide ? null : (
      <div className="overlay">
        <div>
          <div className="text">
            A maximum of 100 columns can be displayed
          </div>
          <button className="add-select-module" onClick={this.onSelectColumns}>Select columns</button>
        </div>
      </div>
    )

    return (
      <div className="outputpane-table">
        <TableInfo
          isReadOnly={isReadOnly}
          wfModuleId={wfModuleId}
          nRows={nRows}
          nColumns={columns ? columns.length : null}
          selectedRowIndexes={selectedRowIndexes}
        />
        <div className="outputpane-data">
          {gridView}
          {maybeOverlay}
        </div>
        {maybeSpinner}
      </div>
    )
  }
}
