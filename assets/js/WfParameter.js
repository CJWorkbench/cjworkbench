// WfParameter - a single editable parameter

import React from 'react'
import MenuParam from './wfparameters/MenuParam'
import ChartParameter from './wfparameters/charts/Chart'
import ChartEditor from './wfparameters/charts/ChartEditor'
import ColumnParam from './wfparameters/ColumnParam'
import ColumnSelector from './wfparameters/ColumnSelector'
import ColumnRenamer from './wfparameters/ColumnRenamer'
import PropTypes from 'prop-types'
import DataVersionSelect from './wfparameters/DataVersionSelect'
import DropZone from './wfparameters/DropZone'
import UpdateFrequencySelect from './wfparameters/UpdateFrequencySelect'
import GoogleConnect from './wfparameters/GoogleConnect'
import FileSelect from './wfparameters/FileSelect'
import WorkbenchAceEditor from './wfparameters/AceEditor'
import CellEditor from './wfparameters/CellEditor'
import Refine from './wfparameters/Refine'
import { csrfToken } from './utils'
import { store, setWfModuleStatusAction } from './workflow-reducer'


export default class WfParameter extends React.Component {

  constructor(props) {
    super(props);

    this.type = this.props.p.parameter_spec.type;
    this.name = this.props.p.parameter_spec.name;

    this.firstProps = true;

    this.keyPress = this.keyPress.bind(this);
    this.blur = this.blur.bind(this);
    this.click = this.click.bind(this);
    this.getInputColNames = this.getInputColNames.bind(this);
    this.getNumericInputColNames = this.getNumericInputColNames.bind(this);
  }

  paramChanged(newVal) {
    this.props.changeParam(this.props.p.id, {value: newVal});
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
          store.dispatch(setWfModuleStatusAction(this.props.wf_module_id, 'error', response.statusText))
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

  // Return array of all columns which contain numeric data. Should be provided by back end.
  getNumericInputColNames() {
    return (
      this.props.api.input(this.props.wf_module_id)
        .then( json => {
            var first_row = json.rows[0];
            var cols = json.columns.filter(column => {
              return isFinite(String(first_row[column]));
            });
            return cols;
        })
    )
  }

  // set contents of HTML input field corresponding to our type
  setInputValue(val) {
    if (this.type === 'string' && this.stringRef) {
      this.stringRef.value = val;
    } else if (this.type === 'checkbox' && this.checkboxRef) {
      this.checkboxRef.value = val;
    } else if ((this.type === 'integer' || this.type == 'float') && this.numberRef) {
      this.numberRef.value = val;
    }
  }

  // We need to update input contents when we get new props
  componentWillReceiveProps(newProps) {
    this.type = newProps.p.parameter_spec.type;
    this.name = newProps.p.parameter_spec.name;

    // If this is our first time through, update form controls to current values
    // this conditional fixes https://www.pivotaltracker.com/story/show/154104065
    if (this.firstProps) {
      this.setInputValue(newProps.p.value);
      this.firstProps = false;
    }
  }

  // Render one of the many parameter types that are specific to a particular module
  render_custom_parameter() {

    if (this.props.p.parameter_spec.id_name === 'chart') {

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

    } else if (this.props.p.parameter_spec.id_name == 'chart_editor') {
      return (
        <ChartEditor
          isReadOnly={ this.props.isReadOnly }
          revision={ this.props.revision }
          wfModuleId={this.props.wf_module_id}
          modelText={this.props.p.value}
          type={ this.props.getParamText('chart_type') }
          api={this.props.api}
        />
      )
    } else if (this.props.p.parameter_spec.id_name == 'version_select') {

      var button = (!this.props.isReadOnly)
        ? <div className='button-blue action-button mt-0' onClick={this.click}>{this.name}</div>
        : null

      return (
        <div className='parameter-margin'>
          <UpdateFrequencySelect
            isReadOnly={this.props.isReadOnly}
            updateSettings={this.props.updateSettings}
            wfModuleId={this.props.wf_module_id}
            api={this.props.api}
            notifications={this.props.notifications}
          />
          <div className="d-flex justify-content-between mt-2">
            <DataVersionSelect
              isReadOnly={this.props.isReadOnly}
              wfModuleId={this.props.wf_module_id}
              revision={this.props.revision}
              api={this.props.api}
              setClickNotification={this.props.setClickNotification}
              notifications={this.props.notifications}
            />
            {button}
          </div>

        </div>
      );
    } else if (this.props.p.parameter_spec.id_name == 'version_select_simpler') {

      return (
        <div className='versionSelect--uploadFile'>
          <DataVersionSelect
            isReadOnly={this.props.isReadOnly}
            wfModuleId={this.props.wf_module_id}
            revision={this.props.revision}
            api={this.props.api}
            setClickNotification={this.props.setClickNotification}
            notifications={this.props.notifications}
          />
        </div>
      );
    } else if (this.props.p.parameter_spec.id_name == 'colrename') {
      var renameParam = this.props.getParamText('newcolnames');
      let saveState = ( state => this.props.setParamText('newcolnames', state) );
      return (
        <div className='parameter-margin'>
          <div className='t-d-gray content-3 label-margin'>Enter new column names</div>
          <ColumnRenamer
            isReadOnly={this.props.isReadOnly}
            renameParam={renameParam}
            saveState={saveState}
            getColNames={this.getInputColNames}
            revision={this.props.revision} />
        </div> );
    } else if (this.props.p.parameter_spec.id_name == 'file') {
      return (
            <DropZone
            wfModuleId={this.props.wf_module_id}
            revision={this.props.revision} />
        );
    } else if (this.props.p.parameter_spec.id_name == 'barchart') {
      return (
        <BarChart
          wf_module_id={this.props.wf_module_id}
          index={this.props.getParamText('column')}
          dataKeys={this.props.getParamText('multicolumn_colorpicker')}
          getParamText={this.props.getParamText}
          setParamText={this.props.setParamText}
        />
      )
    } else if (this.props.p.parameter_spec.id_name == 'connect') {
      return (
        <GoogleConnect
          userCreds={this.props.loggedInUser.google_credentials}
        />
      )
    } else if (this.props.p.parameter_spec.id_name == 'fileselect') {
      return (
        <FileSelect
          api={this.props.api}
          userCreds={this.props.loggedInUser.google_credentials}
          pid={this.props.p.id}
          saveState={state => this.props.setParamText('fileselect', state)}
          getState={() => this.props.getParamText('fileselect')}
        />
      )
    } else if (this.props.p.parameter_spec.id_name == 'code') {
      return (
        <WorkbenchAceEditor
          name={this.props.p.parameter_spec.name}
          onSave={ (val) => { this.paramChanged( val ) } }
          defaultValue={this.props.p.value} />
      )
    } else if (this.props.p.parameter_spec.id_name == 'celledits') {
      return (
        <CellEditor
          edits={this.props.p.value}
          onSave={(val) => { this.paramChanged(val) }}
        />
      )
    } else if (this.props.p.parameter_spec.id_name == 'histogram') {
        var selectedColumn = this.props.getParamText('column');
        //console.log(selectedColumn);
        var existingEdits = this.props.getParamText('edits');
        var saveEdits = (editsJson => this.props.setParamText('edits', editsJson));
        //console.log(existingEdits);
        if(selectedColumn.length < 1) {
            return (<div>Please select a column.</div>)
        }
        return (
            <Refine
                wfModuleId={this.props.wf_module_id}
                selectedColumn={selectedColumn}
                existingEdits={existingEdits}
                saveEdits={saveEdits}
                revision={this.props.revision}
            />
        )
    }
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
          sclass='parameter-base t-d-gray content-2 text-field';
          srows = 1;
        } else {
          sclass='parameter-base t-d-gray content-3 text-field-large';
          srows = 4;
        }

        return (
          <div className='parameter-margin'>
            <div className='label-margin t-d-gray content-3'>{this.name}</div>
            <textarea
              readOnly={this.props.isReadOnly}
              className={sclass}
              rows={srows}
              defaultValue={this.props.p.value}
              onBlur={this.blur}
              onKeyPress={this.keyPress}
              placeholder={this.props.p.parameter_spec.placeholder || ''}
              ref={ el => this.stringRef = el}/>

          </div>
        );

      case 'integer':
      case 'float':
        return (
          <div className='param2-line-margin'>
            <div className='label-margin t-d-gray content-3'>{this.name}</div>
            <input type="text"
              readOnly={this.props.isReadOnly}
              className='number-field parameter-base t-d-gray content-3'
              rows='1'
              defaultValue={this.props.p.value}
              onBlur={this.blur}
              onKeyPress={this.keyPress}
              placeholder={this.props.p.parameter_spec.placeholder || ''}
              ref={ el => this.numberRef = el}/>
          </div>
        );

      case 'button':
        return (
          <div className="parameter-margin d-flex justify-content-end">
            <div className='action-button button-blue' onClick={!this.props.readOnly && this.click}>{this.name}</div>
          </div>
        );
      case 'statictext':
        return (
          <div className='parameter-margin t-m-gray info-2'>{this.name}</div>
        );

      case 'checkbox':
        return (
            <div className='checkbox-wrapper parameter-margin'>
                <div className='d-flex align-items-center'>
                  <input
                    disabled={this.props.isReadOnly}
                    type="checkbox" className="checkbox"
                    checked={this.props.p.value}
                    onChange={this.click}
                    ref={ el => this.checkboxRef = el}/>
                  <div className='t-d-gray content-3 ml-2'>{this.name}</div>
                </div>
            </div>
        );

      case 'menu':
        return (
          <div className='param2-line-margin'>
            <div className='label-margin t-d-gray content-3'>{this.name}</div>
            <MenuParam
              name={this.name}
              items={this.props.p.menu_items}
              selectedIdx={parseInt(this.props.p.value)}
              isReadOnly={this.props.isReadOnly}
              onChange={ idx => { this.paramChanged(idx) }}
            />
          </div> );

      case 'column':
        return (
          <div className='param2-line-margin'>
            <div className='t-d-gray content-3 label-margin'>{this.name}</div>
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
            <div className='t-d-gray content-3 label-margin'>{this.name}</div>
            <ColumnSelector
              selectedCols={this.props.getParamText('colnames')}
              saveState={state => this.props.setParamText('colnames', state) }
              getColNames={this.getInputColNames}
              isReadOnly={this.props.isReadOnly}
              revision={this.props.revision} />
          </div> );


      case 'custom':
        return this.render_custom_parameter();

      default:
        return null;  // unrecognized parameter type
    }
  }
}

WfParameter.propTypes = {
  p:                PropTypes.object.isRequired,  // the actual parameter json
  wf_module_id:     PropTypes.number.isRequired,
  revision:         PropTypes.number.isRequired,
  loggedInUser:     PropTypes.object,             // in read-only there is no user logged in
  api:              PropTypes.object.isRequired,
  updateSettings:   PropTypes.object,             // only for modules that load data
  changeParam:      PropTypes.func.isRequired,
	getParamText:     PropTypes.func.isRequired,
	setParamText:     PropTypes.func.isRequired
};
