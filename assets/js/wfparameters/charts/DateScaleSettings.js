import React from 'react'
import { Button, ButtonGroup } from 'reactstrap'
var DateScaleSettings = require('chartbuilder/src/js/components/shared/DateScaleSettings.jsx');

export default class CjwDateScaleSettings extends DateScaleSettings {
  constructor(props) {
    super(props);
  }

  render() {
    var dateSettings = this.props.scale.dateSettings;
		var showTimezoneSettings = this._showTimezoneSettings(dateSettings.dateFrequency);

		var timezoneInputSettings = null;
    var timezoneDisplaySettings = null;

		if (showTimezoneSettings) {
			var tz_text = this._generateTimezoneText(this.props.now.getMonth());

			timezoneInputSettings = (
				<div>
					<div className="label-margin t-d-gray content-3">Data Timezone</div>
          <select
            className="custom-select parameter-base dropdown-selector"
            onChange={(e) => this._handleDateScaleUpdate("inputTZ", e.target.value)} >
            {this.localizeTimeZoneOptions(this._config.timeZoneOptions, this.props.nowOffset).map((opt) => {
              return (<option key={opt.value} value={opt.value}>{opt.content}</option>)
            })}
          </select>
          <p>{tz_text}</p>
        </div>
      );

      timezoneDisplaySettings = (
        <div>
          <div className="label-margin t-d-gray content-3">Display Timezone</div>
          <ButtonGroup size="lg">
            {this._config.timeDisplayOptions.map((opt) => {
              return (<Button key={opt.value} onClick={() => this._handleDateScaleUpdate("displayTZ", opt.value)}>{opt.content}</Button>)
            })}
          </ButtonGroup>
        </div>
      );
    }
    return (
      <div>
        <div className="row">
          <div className="col-sm-4">
            <div className="label-margin t-d-gray content-3">Date frequency</div>
      			<select
              className="custom-select parameter-base dropdown-selector"
              onChange={(e) => this._handleDateScaleUpdate("dateFrequency", e.target.value)}
              defaultValue={this.props.scale.dateSettings.dateFrequency}>
              {this._config.dateFrequencyOptions.map((opt) => {
                return (
                  <option
                    key={opt.value}
                    value={opt.value}>
                    {opt.content}
                  </option>)
              })}
            </select>
          </div>

          <div className="col-sm-4">
            <div className="label-margin t-d-gray content-3">Date format</div>
      			<select
              className="custom-select parameter-base dropdown-selector"
              onChange={(e) => this._handleDateScaleUpdate("dateFormat", e.target.value)}
              defaultValue={this.props.scale.dateSettings.dateFormat}>
              {this.state.dateFormatOptions.map((opt) => {
                return (
                  <option
                    key={opt.value}
                    value={opt.value}>
                    {opt.content}
                  </option>
                );
              })}
            </select>
          </div>

          <div className="col-sm-4">
            {timezoneInputSettings}
          </div>
        </div>
        <div className="row">
          <div className="col-sm-12">
            {timezoneDisplaySettings}
          </div>
        </div>
      </div>
		)
  }
}
