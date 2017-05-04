// WfParameter - a single editable parameter

import React, { PropTypes } from 'react'
import FetchModal from './FetchModal'
import ChartParameter from './Chart'
import ColumnSelector from './ColumnSelector'

import { csrfToken } from './utils'


export default class WfParameter extends React.Component {

  constructor(props) {
    super(props);

    this.type = this.props.p.parameter_spec.type;
    this.name = this.props.p.parameter_spec.name;

    this.keyPress = this.keyPress.bind(this);
    this.blur = this.blur.bind(this);
    this.click = this.click.bind(this);
    this.getInputColNames = this.getInputColNames.bind(this);
  }

  paramChanged(e) {
    // console.log("PARAM CHANGED");
    var newVal = {};
    newVal[this.type] = e.target.value;
    this.props.changeParam(this.props.p.id, newVal);
  }

  // Save value (and re-render) when user presses enter or we lose focus
  // Applies only to non-multline fields
  keyPress(e) {
    if ((this.type != 'string' || !this.props.p.multiline) && e.key == 'Enter') {
        this.paramChanged(e);
        e.preventDefault();       // eat the Enter so it doesn't get in our input field
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

  // Return array of column names available to us, as a promise
  getInputColNames() {
    var url = '/api/wfmodules/' + this.props.wf_module_id + '/input';
    return fetch(url, { credentials: 'include'})
            .then(response => response.json())
            .then( json => Object.keys(json[0]) );       // get column names from first row of data
  }

  // We need to update input contents when we get new props. Hmm, is there a managed form components library?
  componentWillReceiveProps(newProps) {
    this.type = newProps.p.parameter_spec.type;
    this.name = newProps.p.parameter_spec.name;

    if (this.stringRef) this.stringRef.value = newProps.p.string;
    if (this.numberRef) this.numberRef.value = newProps.p.number;
    if (this.checkboxRef) this.checkboxRef.value = newProps.p.checkbox;
  }


  render() {
    if (!this.props.p.visible) {
      return false; // nothing to see here
    }

    switch (this.type) {
      case 'string':
        // Different size and style if it's a multiline string
        var sclass, srows;
        if (!this.props.p.multiline) {
          sclass='wfmoduleStringInput';
          srows = 1;
        } else {
          sclass='wfmoduleTextInput';
          srows = 4;
        }

        return (
          <div>
            <div>{this.name}:</div>
            <textarea
              className={sclass}
              rows={srows}
              defaultValue={this.props.p.string}
              onBlur={this.blur}
              onKeyPress={this.keyPress}
              ref={ el => this.stringRef = el}/>
          </div>
        );


      case 'number':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea
              className='wfmoduleNumberInput'
              rows='1'
              defaultValue={this.props.p.number}
              onBlur={this.blur}
              onKeyPress={this.keyPress}
              ref={ el => this.numberRef = el}/>
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
                <input
                  type="checkbox"
                  checked={this.props.p.checkbox}
                  onChange={this.click}
                  ref={ el => this.checkboxRef = el}/>
            </div>
        );

      case 'custom':

        if (this.props.p.parameter_spec.id_name == 'chart') {

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

        } else if (this.props.p.parameter_spec.id_name == 'colselect') {

          var selectedCols = this.props.getParamText('colnames');
          var saveState = ( state => this.props.setParamText('colnames', state) );
          return (
            <div>
              <div>{this.name}:</div>
              <ColumnSelector
                selectedCols={selectedCols}
                saveState={saveState}
                getColNames={this.getInputColNames}
                revision={this.props.revision} />
            </div> );
        }

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
