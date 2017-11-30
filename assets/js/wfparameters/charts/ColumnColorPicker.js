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
    console.log(this.props.series);
    if (this.props.series.length > 0) {
      var selectors = [];
      this.props.series.forEach((val, idx, arr) => {
        selectors.push(
          <ChartSeriesChooser
            key={idx}
            value={val.label}
            colorIndex={val.colorIndex}
            index={idx}
            onChange={this.onChange}
          />
        )
      });
      return (<div>{selectors}</div>);
    } else {
      return (<p>ok</p>);
    }
  }
}
