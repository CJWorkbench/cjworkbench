import React from 'react'
import PropTypes from 'prop-types'
import ColumnSelector from './ColumnSelector'
import ChartSeriesChooser from './ChartSeriesChooser'
import {getColor} from './ChartColors'

export default class ColumnColorPicker extends ColumnSelector {
  constructor(props) {
    super(props);
    this.deleteColumn = this.deleteColumn.bind(this);
    this.changeColumn = this.changeColumn.bind(this);
  }

  loadColNames() {
    this.props.getColNames()
      .then(cols => {
        var selected;
        if (this.props.selectedCols === '') {
          selected = cols.map((val, idx, arr) => {
            return {value: val, color: getColor(idx)}
          });
          this.props.saveState(JSON.stringify(selected));
        } else {
          selected = this.state.selected;
        }
        this.setState({colNames: cols, selected: selected});
      });
  }

  parseSelectedCols(selectedColNames) {
    return selectedColNames.length > 0 ? JSON.parse(selectedColNames) : [];   // empty string should give empty array
  }

  deleteColumn(val) {
    var newSelected;
    if (this.state.selected.map(v => v.value).includes(val)) {
      newSelected = this.state.selected.filter( n => n.value !== val );
      this.setState({ selected: newSelected });
      this.props.saveState(JSON.stringify(newSelected));
    }
  }

  changeColumn(newVal) {
    var newSelected = this.state.selected.map((oldVal) => {
      if (oldVal.value === newVal.value) {
        return newVal;
      }
      return oldVal;
    });
    this.props.saveState(JSON.stringify(newSelected));
  }

  render() {
    if (this.state.colNames.length > 0) {
      var selectors = [];
      this.state.selected.forEach((val, idx, arr) => {
        selectors.push(
          <ChartSeriesChooser key={val.value} value={val.value} color={val.color} index={idx} onChange={this.changeColumn} deleteColumn={this.deleteColumn} />
        )
      });
      return (<div>{selectors}</div>);
    } else {
      return false;
    }
  }
}
