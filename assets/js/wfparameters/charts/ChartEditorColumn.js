import React from 'react'
import ColumnColorPicker from  './ColumnColorPicker'
import debounce from 'lodash/debounce'

export default class ChartEditorColumn extends React.Component {
  constructor(props) {
    super(props);
    this.state = JSON.parse(this.props.chartState);
    console.log(this.props);
    this.onChangeChartSettings = this.onChangeChartSettings.bind(this);
    this.onChangeTitle = this.onChangeTitle.bind(this);
    this.saveState = debounce(this.props.saveState, 500);
  }

  onChangeChartSettings(state) {
    let stateCopy = Object.assign({}, this.state);
    stateCopy.chartProps.chartSettings = state;
    this.saveState(JSON.stringify(stateCopy));
  }

  onChangeTitle(e) {
    let stateCopy = Object.assign({}, this.state);
    stateCopy.metadata.title = e.target.value;
    this.setState(stateCopy);
    this.saveState(JSON.stringify(stateCopy));
  }

  render() {
    console.log(this.state);
    if (this.state.chartProps) {
      return (
        <div>
          <ColumnColorPicker
            series={this.state.chartProps.chartSettings}
            saveState={this.onChangeChartSettings}
          />
          <textarea
            className="wfmoduleStringInput t-d-gray content-2 text-field"
            value={this.state.metadata.title}
            onChange={this.onChangeTitle}
          />
        </div>
      )
    } else {
      return (
        <div>errors lol</div>
      )
    }
  }
}
