// Choose some columns

import React from 'react';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { Form, FormGroup, Label, Input } from 'reactstrap';


export default class ColumnSelector extends React.Component {
  constructor(props) {
    super(props);
    this.state = { colNames: [], selected: [] };
    this.clicked = this.clicked.bind(this);
  }

  clicked(e) {
    var checked = e.target.checked;
    var colName = e.target.attributes.getNamedItem('data-name').value;
    var newSelected = undefined;

    if (checked && !(this.state.selected.includes(colName))) {
      // Not there, add it
      newSelected = this.state.selected.slice();
      newSelected.push(colName);
    } else if (!checked && (this.state.selected.includes(colName))) {
      // Is there, remove it
      newSelected = this.state.selected.filter( n => n!=colName )
    }

    if (newSelected) {
      this.setState({colNames: this.state.colNames, selected: newSelected});
      this.props.saveState(newSelected.join())
    }
  }

  // Load column names when first rendered
  componentDidMount() {
    this.props.getColNames()
      .then(cols => {
        var selectedColNames = this.props.loadState().trim();
        selectedColNames = selectedColNames.length>0 ? selectedColNames.split(',') : [];   // empty string should give empty array
        this.setState({colNames: cols, selected: selectedColNames});
      });
  }

  render() {
    // use nowrap style to ensure checkbox label is always on same line as checkbox
    const checkboxes = this.state.colNames.map( n => {
      return (
        <div className='col-sm' style={{'white-space': 'nowrap'}} key={n}>
          <label className='mr-1'>{n}</label>
          <input type='checkbox' checked={this.state.selected.includes(n)} onChange={this.clicked} data-name={n}></input>
        </div>);
      });

    return (
      <div className='container'>
        <div className='row'>
          { checkboxes }
        </div>
      </div>
    );
  }
}

ColumnSelector.propTypes = {
  saveState:    React.PropTypes.func,
  loadState:    React.PropTypes.func,
  getColNames:  React.PropTypes.func
};




