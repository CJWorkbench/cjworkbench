// ---- TableView ----
// Displays a module's rendered output, if any
// Handles paged loading of data, which also means it decides when to turn the OutputPane spinner on

import React from 'react'
import PropTypes from 'prop-types'
import DataGrid from "./DataGrid";
import update from 'immutability-helper'
import * as EditCells from './EditCells'

export function mockAddCellEdit(fn) {
  EditCells.addCellEdit = fn;
}

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

    this.loading = false;

    // constants to control loading behaviour
    this.initialRows = 120;   // because react-data-grid seems to preload to 100
    this.preloadRows = 20;    // get new rows when we are this close to the end
    this.deltaRows = 100;     // get this many new rows at a time
  }

  // safe wrapper as setBusySpinner prop is optional
  setBusySpinner(visible) {
    if (this.props.setBusySpinner)
      this.props.setBusySpinner(visible);
  }

  // Load table data from render API
  loadTable(id, toRow) {
    if (id) {
      // console.log("Asked to load to " + toRow );

      this.loading = true;
      this.setBusySpinner(true);

      this.props.api.render(id, this.state.lastLoadedRow, toRow)
        .then(json => {

          // console.log("Got data to " + json.end_row);
          // Add just retrieved rows to current data, if any
          if (this.state.tableData) {
            json.rows = this.state.tableData.rows.concat(json.rows);
            json.start_row = 0;  // no one looks at this currently, but they might
          }

          // triggers re-render
          this.loading = false;
          this.setBusySpinner(false);
          this.setState({
            tableData: json,
            lastLoadedRow : json.end_row,
          });
        });
    }
  }

  // Completely reload table data -- preserves visibility of old data while we wait
  refreshTable(id) {
    if (id) {
      this.loading = true;
      this.setBusySpinner(true);

      this.props.api.render(id, 0, this.initialRows)
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

  // Load first 100 rows of table when first rendered
  componentDidMount() {
    this.loadTable(this.props.id, this.initialRows);
  }

  // If the revision changes from under us, or we are displaying a different output, reload the table
  componentWillReceiveProps(nextProps) {
    if (this.props.revision !== nextProps.revision || this.props.id !== nextProps.id) {
        this.refreshTable(nextProps.id);
    }
  }

  emptyRow() {
    return this.state.tableData.columns.reduce( (obj,col) => { obj[col]=null; return obj; }, {} );
  }

  getRow(i) {
    if (this.state.tableData) {

      // Time to load more rows?
      if (!this.loading) {
        var target = Math.min(i + this.preloadRows, this.state.tableData.total_rows);  // don't try to load past end of data
        if (target > this.state.lastLoadedRow) {
          this.loadTable(this.props.id, this.state.lastLoadedRow + this.deltaRows);
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

      // Change just this one row, keeping as much of the old tableData as possible
      let newRows = update(this.state.tableData.rows, {[row]: {$merge: {[colName]: newVal}}});
      let newTableData = update(this.state.tableData, {$merge: { rows: newRows }});
      this.setState({ tableData: newTableData });

      EditCells.addCellEdit(this.props.id, {row: row, col: colName, value: newVal})

    } else {
      console.log('However did you edit a row that wasn\'t loaded?')
    }
  }

  render() {
    var tableData = this.props.tableData;

    // Make a table component if we have the data
    var nrows = 0;
    var ncols = 0;
    var gridView = null;
    if (this.props.id && this.state.tableData && this.state.tableData.total_rows>0) {
      gridView =
        <div className="outputpane-data">
          <DataGrid
            totalRows={this.state.tableData.total_rows}
            columns={this.state.tableData.columns}
            getRow={this.getRow}
            resizing={this.props.resizing}
            onEditCell={this.onEditCell}
          />
        </div>
      nrows = this.state.tableData.total_rows;
      ncols = this.state.tableData.columns.length;
    } else {
      // Empty grid, big enough to fill screen.
      // 50 rows by five blank columns (each with a different number of spaces, for unique names)
      gridView =
        <div className="outputpane-data">
          <DataGrid
            totalRows={50}
            columns={['',' ','   ','    ','     ','      ']}
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
