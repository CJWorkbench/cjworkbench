// WfParameter - a single editable parameter

import React, { PropTypes } from 'react'
import FetchModal from './FetchModal'
import ChartParameter from './Chart'
import { csrfToken } from './utils'


export default class WfParameter extends React.Component {

  constructor(props) {
    super(props);

    this.type = this.props.p.parameter_spec.type;
    this.name = this.props.p.parameter_spec.name;

    this.keyPress = this.keyPress.bind(this);
    this.blur = this.blur.bind(this);
    this.click = this.click.bind(this);
  }

  paramChanged(e) {
    // console.log("PARAM CHANGED");
    var newVal = {};
    newVal[this.type] = e.target.value;
    this.props.changeParam(this.props.p.id, newVal);
  }

  // Save value (and re-render) when user presses enter or we lose focus
  // Applies only to non-text fields
  keyPress(e) {
    if (this.type != 'text' && e.key == 'Enter') {
        this.paramChanged(e);
        e.preventDefault();       // eat the Enter so it doesn't get in out input field
    }
  }

  blur(e) {
    this.paramChanged(e);
  }

  // Send event to server for button click
  click(e) {
    if (this.type == 'button') {
      var url = '/api/parameters/' + this.props.p.id + '/event';
      var eventData = {'type': 'click'};
      fetch(url, {
        method: 'post',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(eventData)
      }).then(response => {
        if (!response.ok)
          store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'error', response.statusText))
      });
    }
    if (this.type == 'checkbox') {
        var newVal = {};
        newVal[this.type] = e.target.checked;
        this.props.changeParam(this.props.p.id, newVal);
    }
  }

  render() {
    if (!this.props.p.visible) {
      return false; // nothing to see here
    }

    switch (this.type) {
      case 'string':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleStringInput' rows='1' defaultValue={this.props.p.string} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'number':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleNumberInput' rows='1' defaultValue={this.props.p.number} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'text':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleTextInput' rows='4' defaultValue={this.props.p.text} onBlur={this.blur} onKeyPress={this.keyPress} />
          </div>
        );

      case 'button':
        return (
          <div>
            <button className='btn btn-primary' onClick={this.click}>{this.name}</button>
            <FetchModal />
          </div>
        );

      case 'checkbox':
        return (
            <div>
                <label className='mr-1'>{this.name}:</label>
                <input type="checkbox" checked={this.props.p.checkbox} onChange={this.click}></input>
            </div>
        );

      case 'custom':

        // Load and save chart state, image to hidden parameters
        var loadState = ( () => this.props.getParamText('chartstate') );
        var saveState = ( state => this.props.setParamText('chartstate', state) );

        var saveImageDataURI = ( state => this.props.setParamText('chart', state) );

        return (
          <div>
            <a href={'/public/paramdata/live/' + this.props.p.id + '.png'}>PNG</a>
            <ChartParameter
              wf_module_id={this.props.wf_module_id}
              revision={this.props.revision}
              saveState={saveState}
              loadState={loadState}
              saveImageDataURI={saveImageDataURI}
            />
          </div>
        );

      default:
        return null;  // unrecognized parameter type
    }
  }
}

WfParameter.propTypes = {
  p:                React.PropTypes.object,
  wf_module_id:     React.PropTypes.number,
	revision:         React.PropTypes.number,
  changeParam:      React.PropTypes.func,
	getParamText:     React.PropTypes.func,
	setParamText:     React.PropTypes.func,
};
