// UI for a single module within a workflow

import React from 'react'

// Libraries to provide a collapsable table view
var Collapse = require('pui-react-collapse').Collapse;
const {Table, Column, Cell} = require('fixed-data-table');
require('fixed-data-table/dist/fixed-data-table.min.css');

// ---- WfParameter - a single editable parameter ----

class WfParameter extends React.Component {

  constructor(props) {
    super(props)

    this.type = this.props.p.parameter_spec.type;
    this.name = this.props.p.parameter_spec.name;

    this.keyPress = this.keyPress.bind(this);
    this.blur = this.blur.bind(this);
  }

  paramChanged(e) {
    var newVal = {};
    newVal[this.type] = e.target.value;
    this.props.onParamChanged(this.props.p.id, newVal);
  }

  // Save value (and re-render) when user presses enter or we lose focus
  // Applies only to non-text fields
  keyPress(e) {
    if (this.type != 'text' && e.key == 'Enter') {
        this.paramChanged(e);
        e.preventDefault();       // eat the Enter so it doesn't get in out input field
    }
  }

  blur(e) {
    this.paramChanged(e);
  }

  render() {
    switch (this.type) {
      case 'string':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleStringInput' rows='1' defaultValue={this.props.p.string} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'number':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleNumberInput' rows='1' defaultValue={this.props.p.number} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'text':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleTextInput' rows='4' defaultValue={this.props.p.text} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'button':
        return (
          <div>
            <button className='wfmoduleButton'>{this.name}</button>
          </div>
        );

      default:
        return null;  // unrecognized parameter type
    }
  }
}

// ---- Status Light ----
// Ready, Busy, or Error
class StatusLight extends React.Component {
  render() {
    return <div className={this.props.status + '-light'}></div>
  }
}

// ---- TableView ----
// Displays the module's rendered output, if any

class TableView extends React.Component {
  render() {
    var tableData = this.props.tableData;

    // Generate the table if there's any data
    var colNames = Object.keys(tableData);
    if (colNames.length > 0) {

      var rowCount = tableData[colNames[0]].length;  // +1 for header row
      var cols = colNames.map( colName => {
        return(
          <Column
            key={colName}
            header={<Cell>{colName}</Cell>}
            cell={props => (
              <Cell {...props}>
                {tableData[colName][props.rowIndex]}
              </Cell>
            )}
            width={100}
          />
        )
      });

      var table =
        <Collapse header='Output'>
          <Table
            rowsCount={rowCount}
            rowHeight={50}
            headerHeight={50}
            width={200}
            height={(rowCount+1)*50}>
            {cols}
          </Table>
        </Collapse>;

    }  else {
      var table = <p>(no data)</p>;
    }

    return table;
  }
}



// ---- WfModule ----

export default class WfModule extends React.Component {
  constructor(props) {
    super(props);
    this.state = { tableData: {} };
  }

  // Load table data from render API
  loadTable() {
    var wfmodule = this.props['data-wfmodule'];
    var url = '/api/wfmodules/' + wfmodule.id + '/render';
    var self=this;
    fetch(url)
      .then(response => response.json())
      .then(json => {
        self.setState( { tableData : json } );
        }); // triggers re-render
  }

  // Load table when first rendered
  componentDidMount() {
    this.loadTable()
  }

  // If the revision changes from under us reload the table, which will trigger a setState and re-render
  componentWillReceiveProps(nextProps) {
    if (this.props['data-revision'] != nextProps['data-revision'])
      this.loadTable();
  }

  render() {
    var module = this.props['data-wfmodule']['module'];
    var params= this.props['data-wfmodule']['parameter_vals'];
    var status = this.props['data-wfmodule']['status']
    var tableData = this.state.tableData;
    var onParamChanged = this.props['data-onParamChanged'];

    // Each parameter gets a WfParameter
    var paramdivs = params.map((ps, i) => { return <WfParameter p={ps} key={i} onParamChanged={onParamChanged} /> } );

    // Putting it all together: name, parameters, output
    return (
      <div {...this.props} className="module-li">
        <div>
          <h1 className='moduleName'>{module.name}</h1>
          <StatusLight status={status}/>
        </div>
        <div style={{'clear':'both'}}></div>
        {paramdivs}
        <TableView tableData={tableData}/>
      </div>
    ); 
  } 
}
