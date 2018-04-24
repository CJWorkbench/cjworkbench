// ---- TableView ----
// Displays a module's rendered output, if any
// Handles paged loading of data, which also means it decides when to turn the OutputPane spinner on

import React from 'react'
import PropTypes from 'prop-types'
import DataGrid from "./DataGrid";
import update from 'immutability-helper'
import * as EditCells from './EditCells'
import * as SortFromTable from './SortFromTable'

export function mockAddCellEdit(fn) {
  EditCells.addCellEdit = fn;
}

// Constants to control loading behaviour. Exported so they are accessible to tests
export const initialRows = 200;   // because react-data-grid seems to preload to 100
export const preloadRows = 100;    // load when we have less then this many rows ahead
export const deltaRows = 200;     // get this many rows at a time (must be > preloadRows)

export default class TableView extends React.Component {

  constructor(props) {
    super(props);

    // componentDidMount will trigger first load
    this.state = {
        tableData: null,
        lastLoadedRow : 0,
        leftOffset : 0,
        initLeftOffset: 0,
    };

    this.getRow = this.getRow.bind(this);
    this.onEditCell = this.onEditCell.bind(this);
    this.onSort = this.onSort.bind(this);

    this.loading = false;
    this.highestRowRequested = 0;
    this.emptyRowCache = null;
  }

  // safe wrapper as setBusySpinner prop is optional
  setBusySpinner(visible) {
    if (this.props.setBusySpinner)
      this.props.setBusySpinner(visible);
  }


  // Completely reload table data -- puts up spinner, preserves visibility of old data while we wait
  refreshTable(id) {
    if (id) {
      this.loading = true;
      this.highestRowRequested = 0;
      this.emptyRowCache = null;
      this.setBusySpinner(true);

      this.props.api.render(id, 0, initialRows)
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
  loadTable(id, toRow) {
    if (id) {
      this.loading = true;

      // Spinner if we've used up all our preloaded rows (we're now seeing blanks)
      if (toRow >= this.state.lastLoadedRow + preloadRows + deltaRows) {
        this.setBusySpinner(true);
      }

      this.props.api.render(id, this.state.lastLoadedRow, toRow)
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
    this.refreshTable(this.props.id);  // refresh, not load, so we get the spinner
  }

  // If the revision changes from under us, or we are displaying a different output, reload the table
  componentWillReceiveProps(nextProps) {
      console.log("Table props:");
      console.log(nextProps);
    if (this.props.revision !== nextProps.revision || this.props.id !== nextProps.id) {
        this.refreshTable(nextProps.id);
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
          this.loadTable(this.props.id, target);
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
      let oldVal = this.state.tableData.rows[row][colName];
      if (newVal !== String(oldVal)) {
        // Change just this one row, keeping as much of the old tableData as possible
        let newRows = update(this.state.tableData.rows, {[row]: {$merge: {[colName]: newVal}}});
        let newTableData = update(this.state.tableData, {$merge: {rows: newRows}});
        this.setState({tableData: newTableData});

        EditCells.addCellEdit(this.props.id, {row: row, col: colName, value: newVal})
      }
    }
  }

  onSort(sortCol, sortDir) {
      console.log("Sort clicked on " + sortCol);

      SortFromTable.updateSort(this.props.id, {
          column: sortCol,
          direction: sortDir
      });
  }

  render() {
    var tableData = this.props.tableData;

    // Make a table component if we have the data
    var nrows = 0;
    var ncols = 0;
    var gridView = null;
    if (this.props.id && this.state.tableData && this.state.tableData.total_rows>0) {
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
            getRow={this.getRow}
            resizing={this.props.resizing}
            onEditCell={this.onEditCell}
            onSort={this.onSort}
            sortColumn={this.props.sortColumn}
            sortDirection={this.props.sortDirection}
          />
        </div>
      // adds commas to row count
      nrows = new Intl.NumberFormat('en-US').format(this.state.tableData.total_rows);
      ncols = this.state.tableData.columns.length;
    } else {
      // Empty grid, big enough to fill screen.
      // 50 rows by five blank columns (each with a different number of spaces, for unique names)
      gridView =
        <div className="outputpane-data">
          <DataGrid
            totalRows={10}
            columns={['',' ','   ','    ']}
            getRow={() => {return {}}}
          />
      </div>
    }

    return (
      <div className="outputpane-table">
          <div className="outputpane-header d-flex flex-row justify-content-start">
              <div className='d-flex flex-column align-items-center justify-content-center mr-5'>
                  <div className='content-4 t-m-gray mb-2'>Rows</div>
                  <div className='content-2 t-d-gray'>{nrows}</div>
              </div>
              <div className='d-flex flex-column align-items-center justify-content-center'>
                  <div className='content-4 t-m-gray mb-2'>Columns</div>
                  <div className='content-2 t-d-gray'>{ncols}</div>
              </div>
          </div>
          {gridView}
      </div>
    );
  }
}

TableView.propTypes = {
  id:                 PropTypes.number,             // not actually required, could have no selected module
  revision:           PropTypes.number.isRequired,
  api:                PropTypes.object.isRequired,
  resizing:           PropTypes.bool,
  setBusySpinner:     PropTypes.func,
  onEditCell:         PropTypes.func
};
