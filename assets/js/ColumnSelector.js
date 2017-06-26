// Choose some columns

import React from 'react'
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap'
import { Form, FormGroup, Label, Input } from 'reactstrap'
import PropTypes from 'prop-types'


export default class ColumnSelector extends React.Component {
  constructor(props) {
    super(props);
    this.state = { colNames: [], selected: this.parseSelectedCols(props.selectedCols) };
    this.clicked = this.clicked.bind(this);
  }

  // selected columns string -> array of column names
  parseSelectedCols(sc) {
    var selectedColNames =  sc != undefined ? sc.trim() : '';
    return  selectedColNames.length>0 ? selectedColNames.split(',') : [];   // empty string should give empty array
  }

  loadColNames() {
    this.props.getColNames()
      .then(cols => {
        this.setState({colNames: cols, selected: this.state.selected});
      });
  }

  // Load column names when first rendered
  componentDidMount() {
    this.loadColNames();
  }

  // Update our checkboxes when we get new props = new selected columns string
  // And also column names when workflow revision bumps
  componentWillReceiveProps(nextProps) {
    this.setState({colNames: this.state.colNames, selected: this.parseSelectedCols(nextProps.selectedCols)});
    if (this.props.revision != nextProps.revision) {
      this.loadColNames();
    }
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

  render() {
    // use nowrap style to ensure checkbox label is always on same line as checkbox
    const checkboxes = this.state.colNames.map( n => {
      return (
        <div className='col-sm' style={{'whiteSpace': 'nowrap'}} key={n}>
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
  selectedCols: PropTypes.string,
  saveState:    PropTypes.func,
  getColNames:  PropTypes.func,
  revision:     PropTypes.number
};




