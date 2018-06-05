// WfParameter - a single editable parameter

import React from 'react'
import MenuParam from './wfparameters/MenuParam'
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
import ReorderHistory from './wfparameters/ReorderHistory'
import RenameEntries from './wfparameters/RenameEntries'
import { csrfToken } from './utils'
import { store, setWfModuleStatusAction } from './workflow-reducer'
import lessonSelector from './lessons/lessonSelector'
import { connect } from 'react-redux'

const PRESSED_ENTER = true;
const DIDNT_PRESS_ENTER = false;

class TextOrNothing extends React.Component {
  render() {
    if (this.props.text.length > 0) {
      return <div>{this.props.text}</div>;
    } else {
      return null;
    }
  }
}

export default class WfParameter extends React.Component {

  constructor(props) {
    super(props)

    this.firstProps = true;

    this.keyPress = this.keyPress.bind(this);
    this.blur = this.blur.bind(this);
    this.click = this.click.bind(this);
    this.getInputColNames = this.getInputColNames.bind(this);
  }

  get outerDivProps() {
    const { id_name } = this.props.p.parameter_spec

    return {
      className: this.paramClassName,
      'data-name': id_name, // super-useful when inspecting -- e.g., when developing lessons
    }
  }

  get paramClassName() {
    const { id_name, type } = this.props.p.parameter_spec

    const nameParts = id_name.split('|')[0].split('.').slice(1)

    nameParts.unshift(`wf-parameter-${type}`)
    nameParts.unshift('wf-parameter')

    return nameParts.join(' ')
  }

  paramChanged(newVal, pressedEnter) {
    this.props.changeParam(this.props.p.id, {value: newVal, pressed_enter: pressedEnter});
  }

  // Save value (and re-render) when user presses enter (but not on multiline fields)
  // Applies only to non-multiline fields
  keyPress(e) {
    const type = this.props.p.parameter_spec.type

    if (e.key == 'Enter' && (type != 'string' || !this.props.p.parameter_spec.multiline)) {
        this.paramChanged(e.target.value, PRESSED_ENTER);
        e.preventDefault();       // eat the Enter so it doesn't get in our input field
    }
  }

  blur(e) {
    this.paramChanged(e.target.value, DIDNT_PRESS_ENTER); // false = did not press enter
  }

  // Send event to server for button click
  click(e) {
    const type = this.props.p.parameter_spec.type

    // type==custom a hack for version_select type
    if (type == 'button' || type == 'custom') {
      var eventData = {'type': 'click'};
      this.props.api.postParamEvent(this.props.p.id, eventData)
    }

    if (type == 'checkbox') {
      this.paramChanged(e.target.checked, DIDNT_PRESS_ENTER)
    }

    if (type == 'string' && !this.props.isReadOnly) {
      this.stringRef.select();
    }
  }

  // Return array of column names available to us, as a promise
  getInputColNames() {
    return this.props.api.inputColumns(this.props.wf_module_id);
  }

  // set contents of HTML input field corresponding to our type
  setInputValue(val) {
    const type = this.props.p.parameter_spec.type
    if (type === 'string' && this.stringRef) {
      this.stringRef.value = val;
    } else if (type === 'checkbox' && this.checkboxRef) {
      this.checkboxRef.value = val;
    } else if ((type === 'integer' || type == 'float') && this.numberRef) {
      this.numberRef.value = val;
    }
  }

  // We need to update input contents when we get new props
  componentWillReceiveProps(newProps) {
    // If this is our first time through, update form controls to current values
    // this conditional fixes https://www.pivotaltracker.com/story/show/154104065
    if (this.firstProps) {
      this.setInputValue(newProps.p.value);
      this.firstProps = false;
    }
  }

  // Render one of the many parameter types that are specific to a particular module
  render_custom_parameter() {
    const { id_name, name } = this.props.p.parameter_spec

    if (id_name == 'chart_editor') {
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
    } else if (id_name == 'version_select') {

      var button = (!this.props.isReadOnly)
        ? <button className='button-blue action-button mt-0' onClick={this.click}>{name}</button>
        : null

      return (
        <div {...this.outerDivProps}>
          <UpdateFrequencySelect
            wfModuleId={this.props.wf_module_id}
            isReadOnly={this.props.isReadOnly}
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
    } else if (id_name == 'version_select_simpler') {

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
    } else if (id_name == 'colrename') {
      var renameParam = this.props.getParamText('newcolnames');
      let saveState = ( state => this.props.setParamText('newcolnames', state) );
      return (
        <div className=''>
          <ColumnRenamer
            isReadOnly={this.props.isReadOnly}
            renameParam={renameParam}
            saveState={saveState}
            getColNames={this.getInputColNames}
            revision={this.props.revision} />
        </div> );
    } else if (id_name == 'file') {
      return (
            <DropZone
            wfModuleId={this.props.wf_module_id}
            revision={this.props.revision} />
        );
    } else if (id_name == 'connect') {
      return (
        <GoogleConnect
          userCreds={this.props.loggedInUser.google_credentials}
        />
      )
    } else if (id_name == 'fileselect') {
      return (
        <FileSelect
          api={this.props.api}
          userCreds={this.props.loggedInUser.google_credentials}
          pid={this.props.p.id}
          saveState={state => this.props.setParamText('fileselect', state)}
          getState={() => this.props.getParamText('fileselect')}
        />
      )
    } else if (id_name == 'code') {
      return (
        <WorkbenchAceEditor
          name={this.props.p.parameter_spec.name}
          onSave={ (val) => { this.paramChanged( val ) } }
          defaultValue={this.props.p.value} />
      )
    } else if (id_name == 'celledits') {
      return (
        <CellEditor
          edits={this.props.p.value}
          onSave={(val) => { this.paramChanged(val) }}
        />
      )
    } else if (id_name == 'refine') {
        return (
          <Refine
            wfModuleId={this.props.wf_module_id}
            selectedColumn={this.props.getParamText('column')}
            existingEdits={this.props.p.value}
            saveEdits={(val) => this.paramChanged(val)}
            revision={this.props.revision}
            />
        )
    } else if (id_name == 'reorder-history') {
      return (
        <ReorderHistory
          history={this.props.getParamText('reorder-history')}
        />
      )
    } else if (id_name == 'rename-entries') {
      console.log(this.props);
      return (
          <RenameEntries
              displayAll={this.props.getParamText('display-all')}
              entries={this.props.p.value}
              wfModuleId={this.props.wf_module_id}
              paramId={this.props.p.id}
              revision={this.props.revision}
          />
      )
    }
  }

  displayConditionalUI(condition) {
    // Checks if a menu item in the visibility condition is selected
    // If yes, display or hide the item depending on whether we have inverted the visibility condition
    // type is either 'visible_if' or 'visible_if_not'
    if(('id_name' in condition) && ('value' in condition)) {
      // If the condition value is a boolean:
      if (typeof condition['value'] === typeof true) {
        // Just return if it matches or not
        return condition['value'] === this.props.getParamText(condition['id_name']);
        // TODO: Does this also work with strings? Do we want it to?
      }

      // Otherwise, if it's a menu item:
      let condValues = condition['value'].split('|').map(cond => cond.trim());
      let selectionIdx = parseInt(this.props.getParamText(condition['id_name']));
      if(!isNaN(selectionIdx)) {
        let menuItems = this.props.getParamMenuItems(condition['id_name']);
        if(menuItems.length > 0) {
          let selection = menuItems[selectionIdx];
          let selectionInCondition = (condValues.indexOf(selection) >= 0);
          // No 'invert' means do not invert
          if(!('invert' in condition)) {
            return selectionInCondition;
          } else if(!condition['invert']) {
            return selectionInCondition;
          } else {
            return !selectionInCondition;
          }
        }
      }
    }
    // If the visibility condition is empty or invalid, default to showing the parameter
    return true;
  }

  render() {
    const { id_name, name, type, visible_if, visible_if_not } = this.props.p.parameter_spec

    if (!this.props.p.visible) {
      return null // nothing to see here
    }

    if (visible_if) {
      const condition = JSON.parse(visible_if)
      if (!this.displayConditionalUI(condition, 'visible_if')) {
        return null
      }
    }

    if (visible_if_not) {
      const condition = JSON.parse(visible_if_not)
      if (!this.displayConditionalUI(condition, 'visible_if_not')) {
        return null
      }
    }

    switch (type) {
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
          <div {...this.outerDivProps}>
            <div className='label-margin t-d-gray content-3'>{name}</div>
            <textarea
              onBlur={this.blur}
              onKeyPress={this.keyPress}
              onClick={this.click}
              readOnly={this.props.isReadOnly}
              className={sclass}
              name={id_name}
              rows={srows}
              defaultValue={this.props.p.value}
              placeholder={this.props.p.parameter_spec.placeholder || ''}
              ref={ el => this.stringRef = el}
              />
          </div>
        );

      case 'integer':
      case 'float':
        return (
          <div {...this.outerDivProps}>
            <div className='label-margin t-d-gray content-3'>{name}</div>
            <input type="text"
              readOnly={this.props.isReadOnly}
              className='number-field parameter-base t-d-gray content-3'
              name={id_name}
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
          <div {...this.outerDivProps} className={this.paramClassName + ' d-flex justify-content-end'}>
            <div className='action-button button-blue' onClick={!this.props.readOnly && this.click}>{name}</div>
          </div>
        );
      case 'statictext':
        return (
          <div {...this.outerDivProps} className={this.paramClassName + ' t-m-gray info-2'}>{name}</div>
        );

      case 'checkbox':
        return (
          <div {...this.outerDivProps} className={this.paramClassName + ' checkbox-wrapper'}>
            <div className='d-flex align-items-center'>
              <input
                disabled={this.props.isReadOnly}
                type="checkbox" className="checkbox"
                checked={this.props.p.value}
                onChange={this.click}
                name={id_name}
                ref={ el => this.checkboxRef = el}
                id={this.props.p.id} />
              <label htmlFor={this.props.p.id} className='t-d-gray content-3'>{name}</label>
            </div>
          </div>
        );

      case 'menu':
        return (
          <div {...this.outerDivProps}>
            <div className='label-margin t-d-gray content-3'>{name}</div>
            <MenuParam
              name={id_name}
              items={this.props.p.menu_items}
              selectedIdx={parseInt(this.props.p.value)}
              isReadOnly={this.props.isReadOnly}
              onChange={ idx => { this.paramChanged(idx) }}
            />
          </div> );

      case 'column':
        return (
          <div {...this.outerDivProps}>
            <div className='label-margin t-d-gray content-3'>{name}</div>
            <ColumnParam
              selectedCol={this.props.p.value}
              name={id_name}
              getColNames={this.getInputColNames}
              noSelectionText={this.props.p.parameter_spec.placeholder}
              isReadOnly={this.props.isReadOnly}
              revision={this.props.revision}
              onChange={ col => { this.paramChanged(col) }}
            />
          </div> );

      case 'multicolumn':
        return (
          <div {...this.outerDivProps}>
            <div className='t-d-gray content-3 label-margin'>{name}</div>
            <ColumnSelector
              selectedCols={this.props.getParamText('colnames')}
              saveState={state => this.props.setParamText('colnames', state) }
              getColNames={this.getInputColNames}
              name={id_name}
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
  p: PropTypes.shape({
    parameter_spec: PropTypes.shape({
      id_name: PropTypes.string.isRequired,
      type: PropTypes.string.isRequired,
    }).isRequired,
  }).isRequired,
  moduleName:       PropTypes.string.isRequired,
  wf_module_id:     PropTypes.number.isRequired,
  revision:         PropTypes.number.isRequired,
  loggedInUser:     PropTypes.object,             // in read-only there is no user logged in
  api:              PropTypes.object.isRequired,
  updateSettings:   PropTypes.object,             // only for modules that load data
  changeParam:      PropTypes.func.isRequired,
	getParamText:     PropTypes.func.isRequired,
  setParamText:     PropTypes.func.isRequired,
}
