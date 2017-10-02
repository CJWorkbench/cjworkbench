// WfParameter - a single editable parameter

import React from 'react'
import MenuParam from './MenuParam'
import ChartParameter from './Chart'
import ColumnParam from './ColumnParam'
import ColumnSelector from './ColumnSelector'
import ColumnRenamer from './ColumnRenamer'
import PropTypes from 'prop-types'
import DataVersionSelect from './DataVersionSelect'
import DropZone from './DropZone'
import UpdateFrequencySelect from './UpdateFrequencySelect'
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

  paramChanged(newVal) {
    this.props.changeParam(this.props.p.id, {value : newVal});
  }

  // Save value (and re-render) when user presses enter (but not on multiline fields)
  // Applies only to non-multiline fields
  keyPress(e) {
    if (e.key == 'Enter' && (this.type != 'string' || !this.props.p.parameter_spec.multiline)) {
        this.paramChanged(e.target.value);
        e.preventDefault();       // eat the Enter so it doesn't get in our input field
    }
  }

  blur(e) {
    this.paramChanged(e.target.value);
  }

  // Send event to server for button click
  click(e) {

    // type==custom a hack for version_select type
    if (this.type == 'button' || this.type == 'custom') {
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
        if (!response.ok) {
          store.dispatch(wfModuleStatusAction(this.props.wf_module_id, 'error', response.statusText))
        }
      });
    }

    if (this.type == 'checkbox') {
      this.paramChanged(e.target.checked)
    }
  }

  // Return array of column names available to us, as a promise
  getInputColNames() {
    return (
      this.props.api.input(this.props.wf_module_id)
        .then( json => json.columns )
    )
  }

  // We need to update input contents when we get new props. Hmm, is there a managed form components library?
  componentWillReceiveProps(newProps) {
    this.type = newProps.p.parameter_spec.type;
    this.name = newProps.p.parameter_spec.name;

    // update form controls to current values
    if (this.stringRef) this.stringRef.value = newProps.p.value;
    if (this.numberRef) this.numberRef.value = newProps.p.value;
    if (this.checkboxRef) this.checkboxRef.value = newProps.p.value;
  }


  render() {
    if (!this.props.p.visible) {
      return false; // nothing to see here
    }

    switch (this.type) {
      case 'string':
        // Different size and style if it's a multiline string
        var sclass, srows;
        if (!this.props.p.parameter_spec.multiline) {
          sclass='wfmoduleStringInput t-d-gray content-2 text-field';
          srows = 1;
        } else {
          sclass='wfmoduleTextInput t-d-gray info-1 text-field-large';
          srows = 4;
        }

        return (
          <div className='parameter-margin'>
            <div className='label-margin t-d-gray content-3'>{this.name}:</div>
            <textarea
              readOnly={this.props.isReadOnly}
              className={sclass}
              rows={srows}
              defaultValue={this.props.p.value}
              onBlur={this.blur}
              onKeyPress={this.keyPress}
              ref={ el => this.stringRef = el}/>

          </div>
        );

      case 'integer':
        // return (
        //   <div className='parameter-margin'>
        //     <div className='label-margin t-d-gray content-3'>{this.name}:</div>
        //     <textarea
        //       readOnly={this.props.isReadOnly}
        //       className='wfmoduleIntegerInput t-d-gray content-2 input-number'
        //       rows={srows}
        //       defaultValue={this.props.p.value}
        //       onBlur={this.blur}
        //       onKeyPress={this.keyPress}
        //       ref={ el => this.stringRef = el}/>
        //
        //   </div>
        // );
      case 'float':
        return (
          <div className='parameter-margin'>
            <div className='label-margin t-d-gray content-3'>{this.name}:</div>
            <textarea
              readOnly={this.props.isReadOnly}
              className='wfmoduleNumberInput t-d-gray content-2'
              rows='1'
              defaultValue={this.props.p.value}
              onBlur={this.blur}
              onKeyPress={this.keyPress}
              ref={ el => this.numberRef = el}/>
          </div>
        );

      case 'button':
        return (
          <div className='action-button button-blue mb-3' onClick={!this.props.readOnly && this.click}>{this.name}</div>
        );

      case 'checkbox':
        return (
            <div>
                <label className='parameter-margin t-d-gray content-3 mr-2'>{this.name}:</label>
                <input
                  disabled={this.props.isReadOnly}
                  type="checkbox"
                  checked={this.props.p.value}
                  onChange={this.click}
                  ref={ el => this.checkboxRef = el}/>
            </div>
        );

      case 'menu':
        return (<MenuParam
                  name={this.name}
                  items={this.props.p.menu_items}
                  selectedIdx={parseInt(this.props.p.value)}
                  isReadOnly={this.props.isReadOnly}
                  onChange={ idx => { this.paramChanged(idx) }}
                /> );

      case 'column':
        return (
          <div className='parameter-margin'>
            <div className='t-d-gray content-3 label-margin'>{this.name}:</div>
            <ColumnParam
              selectedCol={this.props.p.value}
              getColNames={this.getInputColNames}
              isReadOnly={this.props.isReadOnly}
              revision={this.props.revision}
              onChange={ col => { this.paramChanged(col) }}
            />
          </div> );

      case 'multicolumn':
        return (
          <div className='parameter-margin'>
            <div className='t-d-gray content-3 label-margin'>{this.name}:</div>
            <ColumnSelector
              selectedCols={this.props.getParamText('colnames')}
              saveState={state => this.props.setParamText('colnames', state) }
              getColNames={this.getInputColNames}
              isReadOnly={this.props.isReadOnly}
              revision={this.props.revision} />
          </div> );


      case 'custom':

        if (this.props.p.parameter_spec.id_name == 'chart') {

          // Load and save chart state, image to hidden parameters
          var loadState = ( () => this.props.getParamText('chartstate') );
          var saveState = ( state => this.props.setParamText('chartstate', state) );

          var saveImageDataURI = ( data => this.props.setParamText('chart', data) );

          return (
            <div>
              <a href={'/public/paramdata/live/' + this.props.p.id + '.png'}>PNG</a>
              <ChartParameter
                isReadOnly={this.props.isReadOnly}
                wf_module_id={this.props.wf_module_id}
                revision={this.props.revision}
                saveState={saveState}
                loadState={loadState}
                saveImageDataURI={saveImageDataURI}
              />
            </div>
          );

        } else if (this.props.p.parameter_spec.id_name == 'version_select') {

          var button = (!this.props.isReadOnly)
            ? <div className='button-blue action-button mt-0' onClick={this.click}>{this.name}</div>
            : null

          return (
            <div className='version-box'>
                <DataVersionSelect
                  isReadOnly={this.props.isReadOnly}
                  wfModuleId={this.props.wf_module_id}
                  revision={this.props.revision}
                  api={this.props.api}
                />
                <UpdateFrequencySelect
                  isReadOnly={this.props.isReadOnly}
                  updateSettings={this.props.updateSettings}
                  wfModuleId={this.props.wf_module_id}
                  api={this.props.api}
                />
                {button}
            </div>
          );
        } else if (this.props.p.parameter_spec.id_name == 'colrename') {
          if (this.props.getParamText('newcolnames') == '')
            var newNameCols = this.props.getParamText('colnames');
          else
            var newNameCols = this.props.getParamText('newcolnames');
          var saveState = ( state => this.props.setParamText('newcolnames', state) );
          return (
            <div>
              <div>{this.name}:</div>
              <ColumnRenamer
                isReadOnly={this.props.isReadOnly}
                newNameCols={newNameCols}
                saveState={saveState}
                getColNames={this.getInputColNames}
                revision={this.props.revision} />
            </div> );
        } else if (this.props.p.parameter_spec.id_name == 'file') {
          return (
                <DropZone
                wfModuleId={this.props.wf_module_id} />
            );
        }


      default:
        return null;  // unrecognized parameter type
    }
  }
}

WfParameter.propTypes = {
  p:                PropTypes.object.isRequired,  // the actual parameter json
  wf_module_id:     PropTypes.number.isRequired,
  revision:         PropTypes.number.isRequired,
  api:              PropTypes.object.isRequired,
  // only for "Load From Url"
  updateSettings:   PropTypes.object,
  changeParam:      PropTypes.func.isRequired,
	getParamText:     PropTypes.func.isRequired,
	setParamText:     PropTypes.func.isRequired
};
