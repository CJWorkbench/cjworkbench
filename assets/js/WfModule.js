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
    this.click = this.click.bind(this);
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

  // Send event to server for button click
  click(e) {
    if (this.type == 'button') {
      var url = '/api/parameters/' + this.props.p.id + '/event';
      var eventData = {'type': 'click'};
      fetch(url, {
        method: 'post',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(eventData)
      }) // no .then, events act through the websocket channel
    }
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
            <button className='wfmoduleButton' onClick={this.click}>{this.name}</button>
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
  constructor(props) {
    super(props);
    this.state = { tableData: [] };
  }


  // Load table data from render API
  loadTable() {
    var url = '/api/wfmodules/' + this.props.wf_module_id  + '/render';
    var self=this;
    console.log("Loading table data for module " + this.props.wf_module_id )
    fetch(url)
      .then(response => response.json())
      .then(json => {
        console.log("Got table data for module " + this.props.wf_module_id )
        self.setState( { tableData : json } );
        }); // triggers re-render
  }

  // Load table when first rendered
  componentDidMount() {
    this.loadTable()
  }

  // If the revision changes from under us reload the table, which will trigger a setState and re-render
  componentWillReceiveProps(nextProps) {
    if (this.props.revision != nextProps.revision)
      this.loadTable();
  }

  shouldComponentUpdate(nextProps, nextState) {
    var update = (this.props.revision != nextProps.revision) ||
                  (this.state.tableData.length == 0 && nextState.tableData.length > 0);
//    console.log("shouldComponentUpdate " + this.props.wf_module_id + " returning " + String(update));
    return update
  }

  render() {
    var tableData = this.state.tableData;

    // Generate the table if there's any data
    if (tableData.length > 0) {

      var colNames = Object.keys(tableData[0]);
      var rowCount = tableData.length;
      var cols = colNames.map( colName => {
        return(
          <Column
            key={colName}
            header={<Cell>{colName}</Cell>}
            cell={props => (
              <Cell {...props}>
                {tableData[props.rowIndex][colName]}
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
            width={500}
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

  render() {
    var module = this.props['data-wfmodule']['module'];
    var params= this.props['data-wfmodule']['parameter_vals'];
    var status = this.props['data-wfmodule']['status']
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
        <TableView wf_module_id={this.props['data-wfmodule'].id} revision={this.props['data-revision']}/>
      </div>
    ); 
  } 
}
