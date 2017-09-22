import React from 'react';
import { Bar } from 'nivo';
import ChartSeriesChooser from './ChartSeriesChooser';

export default class BarChart extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      data: null,
      height: 500,
      width: 500,
      indexKeys: null,
      index: null,
      dataKeys: null
    }
    this.onIndexChange = this.onIndexChange.bind(this);
    this.onKeyChange = this.onKeyChange.bind(this);
  }

  loadChart() {
    var self = this;
    var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
    fetch(url, { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        self.setState({data:json.rows, indexKeys:json.columns});
      });
  }

  componentDidMount() {
    this.loadChart();
  }

  onIndexChange(event) {
    this.setState({index:event.target.value});
  }

  onKeyChange(event) {
    this.setState({dataKeys:[event.target.value]});
  }

  render() {
    var chart;
    if (this.state.data && this.state.dataKeys && this.state.index) {
      chart = <Bar
        data={this.state.data}
        width={this.state.width}
        height={this.state.height}
        indexBy={this.state.index}
        keys={this.state.dataKeys}
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
      />
    }
    if (this.state.data) {
      var indexKeyOptions = [<option disabled selected value className='dropdown-menu-item t-d-gray content-3'>Choose a column</option>]
      this.state.indexKeys.forEach((name, index) => {
        indexKeyOptions.push(<option key={index} value={name} className='dropdown-menu-item t-d-gray content-3'>{name}</option>);
      });
      return (
        <div>
          {chart}
          <select
            className='custom-select dropdown-selector'
            value={this.state.index}
            onChange={this.onIndexChange}
          >
            {indexKeyOptions}
          </select>

          <select
            className='custom-select dropdown-selector'
            value={this.state.dataKeys}
            onChange={this.onKeyChange}
          >
            {indexKeyOptions}
          </select>
        </div>
      );
    } else {
      return false;
    }
  }
}
