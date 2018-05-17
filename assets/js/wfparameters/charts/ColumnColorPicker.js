import React from 'react'
import PropTypes from 'prop-types'
import ChartSeriesChooser from './ChartSeriesChooser'
import {getColor} from './ChartColors'

export default class ColumnColorPicker extends React.Component {
  constructor(props) {
    super(props);
    this.onChange = this.onChange.bind(this);
  }

  onChange(idx, newProps) {
    // This is somehow still the reccomended way to clone an array of objects
    var newSeries = JSON.parse(JSON.stringify(this.props.series));

    // Object.assign mutates the original object if the first argument
    // is not an empty object
    Object.assign(newSeries[idx], newProps)

    this.props.saveState(newSeries);
  }

  render() {
    if (this.props.series.length > 0) {
      const selectors = this.props.series.map((val, idx) => (
        <ChartSeriesChooser
          key={idx}
          label={val.label}
          colName={val.colName}
          colorIndex={val.colorIndex}
          index={idx}
          onChange={this.onChange} />
      ))
      return (<div>{selectors}</div>);
    } else {
      return (<p>ok</p>);
    }
  }
}
