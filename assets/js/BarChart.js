import React from 'react';
import { Bar } from 'nivo';
import {FormGroup, Input} from 'reactstrap';
import ChartSeriesChooser from './ChartSeriesChooser';

export default class BarChart extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      data: null,
      height: 500,
      width: 430,
      indexBy: null,
      dataKeys: null,
      colorKeys: null,
    }
    this.getColorFromKeys = this.getColorFromKeys.bind(this);
  }

  componentDidMount() {
    this.loadChart();
    if(this.props.dataKeys) {
      this.parseColors(this.props);
    }
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.dataKeys === this.props.dataKeys) {
      return false;
    }
    this.parseColors(nextProps);
  }

  loadChart() {
    var self = this;
    var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
    fetch(url, { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        var firstRow = json.rows[0];
        var firstNonNumericCol;
        for (var i=0;i<json.columns.length;i++) {
          if(!isFinite(String(firstRow[json.columns[i]]))) {
            firstNonNumericCol = json.columns[i];
            console.log(firstNonNumericCol);
            break;
          }
        }
        self.setState({
          indexBy: firstNonNumericCol,
          data: json.rows,
        });
      });
  }

  parseColors(props) {
    var colorKeys = {};

    JSON.parse(props.dataKeys).forEach(
      (val) => {
        colorKeys[val.value] = val.color;
      }
    );

    this.setState({
      dataKeys: Object.keys(colorKeys),
      colorKeys: colorKeys,
    });
  }

  getColorFromKeys(data) {
    return this.state.colorKeys[data.id];
  }

  render() {
    if (this.state.data &&
      this.state.indexBy !== '' &&
      this.props.dataKeys !== '') {
      return (<Bar
        data={this.state.data}
        width={this.state.width}
        height={this.state.height}
        indexBy={this.state.indexBy}
        keys={this.state.dataKeys}
        colorBy={this.getColorFromKeys}
        layout="horizontal"
        enableLabel={false}
        axisBottom={{
            "orient": "bottom",
            "tickSize": 5,
            "tickPadding": 5,
            "tickRotation": 90,
        }}
        axisLeft={{
            "orient": "left",
            "tickSize": 5,
            "tickPadding": 5,
            "tickRotation": 30,
        }}
        margin={{
          "top": 50,
          "right": 10,
          "bottom": 50,
          "left": 160
        }}
        padding={0.2}
      />);
    } else {
      return false;
    }
  }
}
