// ---- TableView ----
// Displays a module's rendered output, if any
// Handles paged loading of data, which also means it decides when to turn the OutputPane spinner on

import React from 'react'
import PropTypes from 'prop-types'
import DataGrid from "./DataGrid";
import ExportModal from "./ExportModal"
import update from 'immutability-helper'
import * as UpdateTableAction from './UpdateTableAction'
import {findParamValByIdName} from "./utils";

// Constants to control loading behaviour. Exported so they are accessible to tests
export const initialRows = 200;   // because react-data-grid seems to preload to 100
export const preloadRows = 100;    // load when we have less then this many rows ahead
export const deltaRows = 200;     // get this many rows at a time (must be > preloadRows)

export default class TableView extends React.PureComponent {
  static propTypes = {
    selectedWfModuleId: PropTypes.number,             // not actually required, could have no selected module
    revision:           PropTypes.number.isRequired,
    api:                PropTypes.object.isRequired,
    isReadOnly:         PropTypes.bool.isRequired,
    resizing:           PropTypes.bool.isRequired,
    setBusySpinner:     PropTypes.func,
    showColumnLetter:   PropTypes.bool.isRequired,
    sortColumn:         PropTypes.string,
    sortDirection:      PropTypes.number,
  };

  constructor(props) {
    super(props);

    // componentDidMount will trigger first load
    this.state = {
      tableData: null,
      lastLoadedRow : 0,
      leftOffset : 0,
      initLeftOffset: 0,
      exportModalOpen: false,
    };

    this.getRow = this.getRow.bind(this);
    this.onEditCell = this.onEditCell.bind(this);
    this.setSortDirection = this.setSortDirection.bind(this);
    this.toggleExportModal = this.toggleExportModal.bind(this);
    this.duplicateColumn = this.duplicateColumn.bind(this);

    this.loading = false;
    this.highestRowRequested = 0;
    this.emptyRowCache = null;
  }

  toggleExportModal() {
    this.setState({ exportModalOpen: !this.state.exportModalOpen });
  }


  // safe wrapper as setBusySpinner prop is optional
  setBusySpinner(visible) {
    if (this.props.setBusySpinner)
      this.props.setBusySpinner(visible);
  }


  // Completely reload table data -- puts up spinner, preserves visibility of old data while we wait
  refreshTable() {
    if (this.props.selectedWfModuleId) {
      this.loading = true;
      this.highestRowRequested = 0;
      this.emptyRowCache = null;
      this.setBusySpinner(true);

      this.props.api.render(this.props.selectedWfModuleId, 0, initialRows)
        .then(json => {
          this.loading = false;
          this.setBusySpinner(false);
          this.setState({
            tableData: json,
            lastLoadedRow: json.end_row,
          });
        })
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

          this.loading = false;
          this.setBusySpinner(false);
          this.setState({
            tableData: json,
            lastLoadedRow : json.end_row,
          });
        });
    }
  }


  componentDidMount() {
    this.refreshTable();  // refresh, not load, so we get the spinner
  }

  // If the revision changes from under us, or we are displaying a different output, reload the table
  componentDidUpdate(prevProps) {
      //console.log("Table props:");
      //console.log(nextProps);
    if (this.props.revision !== prevProps.revision || this.props.selectedWfModuleId !== prevProps.selectedWfModuleId) {
        this.refreshTable();
    }
  }

  emptyRow() {
    if (!this.emptyRowCache)
      this.emptyRowCache = this.state.tableData.columns.reduce( (obj,col) => { obj[col]=null; return obj; }, {} );
    return this.emptyRowCache;
  }

  getRow(i) {
    if (this.state.tableData) {

      // Don't load rows only 100 at a time, if the user scrolls down fast
      this.highestRowRequested = Math.max(this.highestRowRequested, i);

      // Time to load more rows?
      if (!this.loading) {
        let target = Math.max(i, this.highestRowRequested);
        target += preloadRows;
        target = Math.min(target, this.state.tableData.total_rows-1);  // don't try to load past end of data
        if (target >= this.state.lastLoadedRow) {
          target += deltaRows;
          this.loadTable(target);
        }
      }

      // Return the row if we have it
      if (i < this.state.lastLoadedRow ) {
        return this.state.tableData.rows[i];
      } else {
        return this.emptyRow();
      }

    } else {
        // nothing loaded yet
        return null;
    }
  }

  // When a cell is edited we need to 1) update our own state 2) add this edit to an Edit Cells module
  onEditCell(row, colName, newVal) {
    if (row<this.state.lastLoadedRow && this.state.tableData) {    // should always be true if user clicked on cell to edit it

      // Add an edit if the data has actually changed. Cast everything to string for comparisons.
      const oldVal = this.state.tableData.rows[row][colName];
      if (newVal !== (oldVal || '')) {
        // Change just this one row, keeping as much of the old tableData as possible
        const newRows = update(this.state.tableData.rows, {[row]: {$merge: {[colName]: newVal}}});
        const newTableData = update(this.state.tableData, {$merge: {rows: newRows}});
        this.setState({tableData: newTableData});

        UpdateTableAction.updateTableActionModule(this.props.selectedWfModuleId, 'editcells', {row: row, col: colName, value: newVal})
      }
    }
  }

  setSortDirection(sortCol, sortType, sortDirection) {
    UpdateTableAction.updateTableActionModule(this.props.selectedWfModuleId, 'sort-from-table', sortCol, sortType, sortDirection);
      this.refreshTable();
  }

  duplicateColumn(colName) {
    UpdateTableAction.updateTableActionModule(this.props.selectedWfModuleId, 'duplicate-column', colName);
      this.refreshTable();
  }

  render() {
    // Make a table component if we have the data
    var nrows = 0;
    var ncols = 0;
    var gridView = null;

    if (this.props.selectedWfModuleId && this.state.tableData && this.state.tableData.total_rows>0) {
      const { sortColumn, sortDirection, showColumnLetter } = this.props

      // DataGrid is the heaviest DOM tree we have, and it effects the
      // performance of the custom drag layer (and probably everything else). By
      // putting a no-op translate3d property on it, we coerce browsers into
      // rendering it and all of its children in a seperate compositing layer,
      // improving the rendering of everything else in the app.
      gridView =
        <div className="outputpane-data" style={{transform:'translate3d(0, 0, 0)'}}>
          <DataGrid
            totalRows={this.state.tableData.total_rows}
            columns={this.state.tableData.columns}
            columnTypes={this.state.tableData.column_types}
            wfModuleId={this.props.selectedWfModuleId}
            revision={this.props.revision}
            getRow={this.getRow}
            resizing={this.props.resizing}
            onEditCell={this.onEditCell}
            setSortDirection={this.setSortDirection}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            showLetter={showColumnLetter}
            duplicateColumn={this.duplicateColumn}
            onReorderColumns={UpdateTableAction.updateTableActionModule}
            onRenameColumn={UpdateTableAction.updateTableActionModule}
            isReadOnly={this.props.isReadOnly}
          />
        </div>
      // adds commas to row count
      nrows = new Intl.NumberFormat('en-US').format(this.state.tableData.total_rows);
      ncols = this.state.tableData.columns.length;
    } else {
      // Empty grid, big enough to fill screen.
      // 10 rows by four blank columns (each with a different number of spaces, for unique names)
      gridView =
        <div className="outputpane-data">
          <DataGrid
            id={undefined}
            totalRows={10}
            columns={['',' ','   ','    ']}
            getRow={() => {return {}}}
            isReadOnly={this.props.isReadOnly}
            setSortDirection={this.setSortDirection}
            duplicateColumn={this.duplicateColumn}
          />
      </div>
    }

    return (
      <div className="outputpane-table">
          <div className="outputpane-header">
            <div className="container">
              <div className='table-info'>
                  <div className='data'>Rows</div>
                  <div className='value'>{nrows}</div>
              </div>
              <div className='table-info'>
                  <div className='data'>Columns</div>
                  <div className='value'>{ncols}</div>
              </div>
            </div>
            {this.props.selectedWfModuleId ? (
              <div className="export-table" onClick={this.toggleExportModal}>
                <div className="icon-download"></div>
                <span>CSV</span>
                <span className="feed">JSON FEED</span>
                <ExportModal open={this.state.exportModalOpen} wfModuleId={this.props.selectedWfModuleId} onClose={this.toggleExportModal}/>
              </div>
            ) : null}
          </div>
          {gridView}
      </div>
    );
  }
}
