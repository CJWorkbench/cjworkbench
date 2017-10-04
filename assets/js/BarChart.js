import React from 'react';
import { Bar } from 'nivo';
import {FormGroup, Input} from 'reactstrap';
import ChartSeriesChooser from './ChartSeriesChooser';

export default class BarChart extends React.Component {
  constructor(props) {
    super(props);
    this.colorKeys = {};
    JSON.parse(this.props.dataKeys).forEach(
      (val) => {
        this.colorKeys[val.value] = val.color;
      }
    );
    this.state = {
      data: null,
      height: 500,
      width: 500,
      index: null,
      dataKeys: Object.keys(this.colorKeys)
    }
    this.getColorFromKeys = this.getColorFromKeys.bind(this);
  }

  loadChart() {
    var self = this;
    var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
    fetch(url, { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        self.setState({data:json.rows});
      });
  }

  componentDidMount() {
    this.loadChart();
  }

  getColorFromKeys(data) {
    return this.colorKeys[data.id];
  }

  render() {
    if (this.state.data &&
      this.props.index !== '' &&
      this.props.dataKeys !== '') {
      return (<Bar
        data={this.state.data}
        width={this.state.width}
        height={this.state.height}
        indexBy={this.props.index}
        keys={this.state.dataKeys}
        colorBy={this.getColorFromKeys}
        enableLabel={true}
        axisBottom={{
            "orient": "bottom",
            "tickSize": 5,
            "tickPadding": 5,
            "tickRotation": 0,
        }}
        axisLeft={{
            "orient": "left",
            "tickSize": 5,
            "tickPadding": 5,
            "tickRotation": 0,
        }}
        margin={{
          "top": 50,
          "right": 60,
          "bottom": 50,
          "left": 60
        }}
        padding={0.2}
      />);
    } else {
      return false;
    }
  }
}
