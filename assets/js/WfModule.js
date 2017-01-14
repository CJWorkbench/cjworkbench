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

    this.blur = this.blur.bind(this);
  }


  // Save value to server when we lose focus (like user changing fields or clicking on render)
  blur(e) {
    var _body = {};
    _body[this.type] = e.target.value;

    fetch('/api/parameters/' + this.props.p.id, {
      method: 'patch',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(_body)
    })
    .catch( (error) => { console.log('Parameter change failed', error); });
  }

  render() {
    switch (this.type) {
      case 'String':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleStringInput' rows='1' defaultValue={this.props.p.string} onBlur={this.blur}/>
          </div>
        );

      case 'Number':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleNumberInput' rows='1' defaultValue={this.props.p.number} onBlur={this.blur}/>
          </div>
        );

      case 'Text':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleTextInput' rows='4' defaultValue={this.props.p.text} onBlur={this.blur}/>
          </div>
        );
    }
  }
}

// ---- WfModule ----

export default class WfModule extends React.Component {
  constructor(props) {
    super(props);

    this.state = { tableData: {} };
  }

  // Load table data from render API
  componentDidMount() {
    var wfmodule = this.props['data-wfmodule'];
    var url = '/api/wfmodules/' + wfmodule.id + '/render';
    var self=this;
    fetch(url)
      .then(response => response.json())
      .then(json => {
        self.setState( { tableData : json } );
        }); // triggers re-render
  }

  render() {
    var module = this.props['data-wfmodule']['module'];
    var params= this.props['data-wfmodule']['parameter_vals'];
    var tableData = this.state.tableData;

    // Each parameter gets a WfParameter
    var paramdivs = params.map((ps, i) => { return <WfParameter p={ps} key={i} /> } );

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
        </Collapse>

    }  else {
      var table = <p>(no data)</p>
    }

    // Putting it all together: name, parameters, output
    return (
      <div {...this.props} className="module-li">
        <h1>{module.name}</h1>
        {paramdivs}
        {table}
      </div>
    ); 
  } 
}
