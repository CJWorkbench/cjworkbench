// Display of output from currently selected module

import React from 'react'
import TableView from './TableView'
import PropTypes from 'prop-types'
import { OutputIframe } from './OutputIframe'
import Resizable from 're-resizable'
import debounce from 'lodash/debounce'

export default class OutputPane extends React.Component {

  constructor(props) {
    super(props);

    // componentDidMount will trigger first load
    this.state = {
        tableData: null,
        lastLoadedRow : 0,
        leftOffset : 0,
        initLeftOffset: 0,
        width: "100%",
        height: "100%",
        parentBase: null,
        pctBase: null,
        resizing: false,
    };

    this.getRow = this.getRow.bind(this);
    this.resizePaneStart = this.resizePaneStart.bind(this);
    this.resizePane = this.resizePane.bind(this);
    this.resizePaneEnd = this.resizePaneEnd.bind(this);
    this.reset = this.reset.bind(this);

    // loading flag cannot be in state because we need to suppress fetches in getRow, which is called many times in a tick
    this.loading = false;

    // constants to control loading behaviour
    this.initialRows = 120;   // because react-data-grid seems to preload to 100
    this.preloadRows = 20;    // get new rows when we are this close to the end
    this.deltaRows = 100;     // get this many new rows at a time
  }

  // Load table data from render API
  loadTable(id, toRow) {
    if (id) {
      // console.log("Asked to load to " + toRow );

      this.loading = true;
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
          this.setState({
            tableData: json,
            lastLoadedRow : json.end_row
          });

        });
    }
  }

  // Completely reload table data -- preserves visibility of old data while we wait
  refreshTable(id) {
    this.loading = true;
    this.props.api.render(id, 0, this.initialRows)
      .then(json => {
        this.loading = false;
        this.setState({
          tableData: json,
          lastLoadedRow: json.end_row
        });
      })
  }

  // Load first 100 rows of table when first rendered
  componentDidMount() {
    window.addEventListener("resize", debounce(() => { this.reset(this.props.libraryOpen) }, 200));
    this.reset(this.props.libraryOpen);
    this.loadTable(this.props.id, this.initialRows);
  }

  // If the revision changes from under us, or we are displaying a different output, reload the table
  componentWillReceiveProps(nextProps) {
    if (this.props.revision !== nextProps.revision || this.props.id !== nextProps.id) {
        this.refreshTable(nextProps.id);
    }
    if (nextProps.libraryOpen !== this.props.libraryOpen) {
        this.reset(nextProps.libraryOpen, true);
    }
  }

  // Update only when we are not loading
//  shouldComponentUpdate(nextProps, nextState) {
//    return !nextState.loading;
//  }

  emptyRow() {
    return this.state.tableData.columns.reduce( (obj,col) => { obj[col]=null; return obj; }, {} );
  }

  getRow(i) {
    if (this.state.tableData) {

      // Time to load more rows?
      if (!this.loading) {
        var target = Math.min(i + this.preloadRows, this.state.tableData.total_rows);  // don't try to load past end of data
        if (target > this.state.lastLoadedRow) {
          //console.log("Triggered reload at getRow " + i);
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

  getWindowWidth() {
      return window.innerWidth
        || document.documentElement.clientWidth
        || document.body.clientWidth;
  }

  resizePaneStart() {
      this.props.setOverlapping(true);
      this.props.setFocus();
  }

  resizePane(e, direction, ref, d) {
    let offset = this.state.initLeftOffset - d.width;
    this.setState({
        leftOffset: offset,
        resizing: true
    });
  }

  resizePaneEnd(e, direction, ref, d) {
      let width = parseFloat(this.state.width) + ((d.width / this.state.pctBase) * 100) + '%';
      this.setState({
          initLeftOffset: this.state.leftOffset,
          width,
          resizing: false
      });
      this.props.setOverlapping((this.state.leftOffset < 0));
  }

  reset(libraryState, libraryToggle) {
      let libraryOffset = 0;
      let resetWidth;
      let resetOffset;
      let maxWidthOffset = 0;
      let resetMaxWidth;

      if (libraryState === true) {
          maxWidthOffset = 240;
          if (libraryToggle === true) {
              libraryOffset = -140;
          }
      }

      if (libraryState === false) {
          maxWidthOffset = 100;
          if (libraryToggle === true) {
              libraryOffset = 140;
          }

      }

      resetOffset = this.state.leftOffset + libraryOffset;

      if (resetOffset > 0 || this.state.leftOffset === 0) {
          resetOffset = 0;
          resetWidth = '100%';
      } else {
          resetWidth = ((this.state.parentBase.clientWidth - resetOffset) / this.state.parentBase.clientWidth) * 100 + '%';
      }

      resetMaxWidth = ((this.getWindowWidth() - maxWidthOffset) / this.state.parentBase.clientWidth) * 100 + '%';

      if ( parseFloat(resetWidth) > parseFloat(resetMaxWidth) ) {
          resetOffset = resetOffset + ( this.state.parentBase.clientWidth * ( ( parseFloat(resetWidth) - parseFloat(resetMaxWidth) ) / 100 ) );
          resetWidth = resetMaxWidth;
      }

      this.setState({
          leftOffset : resetOffset,
          initLeftOffset: resetOffset,
          width: resetWidth,
          height: "100%",
          maxWidth: resetMaxWidth,
          pctBase: this.state.parentBase.clientWidth,
          overlapping: (resetOffset < 0)
      });
  }

  render() {

    // Make a table component if we have the data
    var tableView = null;
    var nrows = 0;
    var ncols = 0;
    if (this.props.id && this.state.tableData && this.state.tableData.total_rows>0) {
      tableView =
        <div className="outputpane-data">
          <TableView
            totalRows={this.state.tableData.total_rows}
            columns={this.state.tableData.columns}
            getRow={this.getRow}
            resizing={this.state.resizing}
          />
        </div>
      nrows = this.state.tableData.total_rows;
      ncols = this.state.tableData.columns.length;
    }

    return (
        <div className={"outputpane" + (this.props.focus ? " focus" : "")}
             ref={(ref) => this.state.parentBase = ref}
             onClick={this.props.setFocus} >
            <Resizable
                style={{
                    transform: "translateX(" + this.state.leftOffset + "px)"
                }}
                className="outputpane-box"
                enable={{
                    top:false,
                    right:false,
                    bottom:false,
                    left:true,
                    topRight:false,
                    bottomRight:false,
                    bottomLeft:false,
                    topLeft:false
                }}
                size={{
                    width: this.state.width,
                    height: this.state.height,
                }}
                minWidth="100%"
                maxWidth={this.state.maxWidth}
                onResizeStart={this.resizePaneStart}
                onResize={this.resizePane}
                onResizeStop={this.resizePaneEnd} >
                {this.props.htmlOutput &&
                <OutputIframe
                    id="output_iframe"
                    selectedWfModuleId={this.props.selectedWfModuleId}
                    revision={this.props.revision}
                />
                }
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
                    {tableView}
                </div>
            </Resizable>
        </div>
    );
  }
}

OutputPane.propTypes = {
  id:       PropTypes.number,
  revision: PropTypes.number,
  api:      PropTypes.object.isRequired
};
