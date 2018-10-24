// WfParameter - a single editable parameter

import React from 'react'
import PropTypes from 'prop-types'
import MenuParam from './wfparameters/MenuParam'
import ChartSeriesMultiSelect from './wfparameters/ChartSeriesMultiSelect'
import ColumnParam from './wfparameters/ColumnParam'
import ColumnSelector from './wfparameters/ColumnSelector'
import DataVersionSelect from './wfparameters/DataVersionSelect'
import DropZone from './wfparameters/DropZone'
import VersionSelect from './wfparameters/VersionSelect'
import OAuthConnect from './wfparameters/OAuthConnect'
import GoogleFileSelect from './wfparameters/GoogleFileSelect'
import LazyAceEditor from './wfparameters/LazyAceEditor'
import CellEditor from './wfparameters/CellEditor'
import NumberField from './wfparameters/NumberField'
import Refine from './wfparameters/Refine'
import ReorderHistory from './wfparameters/ReorderHistory'
import RenameEntries from './wfparameters/RenameEntries'
import SingleLineTextField from './wfparameters/SingleLineTextField'
import RadioParam from './wfparameters/RadioParam'
//import MapLocationDropZone from './wfparameters/choropleth/MapLocationDropZone'
//import MapLocationPresets from './wfparameters/choropleth/MapLocationPresets'
//import MapLayerEditor from './wfparameters/choropleth/MapLayerEditor'

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

export default class WfParameter extends React.PureComponent {
  static propTypes = {
    p: PropTypes.shape({
      id: PropTypes.number.isRequired,
      value: PropTypes.any, // initial value -- value in Redux store
      parameter_spec: PropTypes.shape({
        id_name: PropTypes.string.isRequired,
        type: PropTypes.string.isRequired,
      }).isRequired,
    }).isRequired,
    moduleName:     PropTypes.string.isRequired,
    wfModuleStatus: PropTypes.string, // module status, or null for placeholder
    wfModuleError:  PropTypes.string, // module-level error message
    wfModuleId: PropTypes.number.isRequired,
    inputWfModuleId: PropTypes.number, // or null
    inputDeltaId: PropTypes.number, // or null
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    })), // or null
    lastRelevantDeltaId: PropTypes.number, // or null
    api:            PropTypes.object.isRequired,
    updateSettings: PropTypes.object,             // only for modules that load data
    isReadOnly:     PropTypes.bool.isRequired,
    isZenMode:      PropTypes.bool.isRequired,
    changeParam:    PropTypes.func.isRequired,
    getParamId:     PropTypes.func.isRequired,
    getParamText:   PropTypes.func.isRequired,
    setParamText:   PropTypes.func.isRequired,
    // "new-style" API: what it should have been all along. Normal React state stuff.
    onChange: PropTypes.func.isRequired, // func(idName, newValue) => undefined
    onSubmit: PropTypes.func.isRequired, // func() => undefined
    onReset: PropTypes.func.isRequired, // func(idName) => undefined
    value: PropTypes.any // value user has edited but not saved -- usually p.value, empty is allowed
  }

  constructor(props) {
    super(props)

    this.state = {
      value: this.props.p.value
    }
  }

  componentDidUpdate (prevProps) {
    if (prevProps.p.value !== this.props.p.value) {
      // Overwrite user's changes to value, if there are any.
      // More often, when this value changes the user _hasn't_ been editing
      // values, so we want to change the value to what the server says it is.
      this.setState({ value: this.props.p.value })
    }
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

  get idName () {
    return this.props.p.parameter_spec.id_name
  }

  onChange = (value) => {
    this.props.onChange(this.idName, value)
  }

  onSubmit = () => {
    this.props.onSubmit()
  }

  onReset = () => {
    this.props.onReset(this.idName)
  }

  paramChanged = (newVal) => {
    this.props.changeParam(this.props.p.id, { value: newVal })
  }

  /**
   * "old-style" form: submit just this param on blur.
   */
  blur = (e) => {
    this.paramChanged(e.target.value)
  }

  onClickCheckbox = (ev) => {
    this.paramChanged(ev.target.checked)
  }

  getInputValueCounts = () => {
    return this.props.api.valueCounts(
      this.props.inputWfModuleId,
      this.props.getParamText('column')
    )
  }

  onChangeGoogleFileSelectJson = (json) => {
    this.props.onChange(this.props.name, json)
    this.props.onSubmit()
  }

  onChangeYColumns = (arr) => {
    this.props.setParamText('y_columns', JSON.stringify(arr))
  }

  colRenameSaveState = (state) => {
    this.props.setParamText('newcolnames', state)
  }

  onColumnSelectorChange = (value) => {
    this.props.setParamText('colnames', value)
  }

  render_secret_parameter() {
    const { id_name } = this.props.p.parameter_spec
    const { id, value } = this.props.p
    const secretName = value ? (value.name || null) : null

    switch (id_name) {
      case 'google_credentials':
      case 'twitter_credentials':
        return (
          <OAuthConnect
            paramId={id}
            api={this.props.api}
            secretName={secretName}
            />
        )

     default:
       return (<p className="error">Secret type {id_name} not handled</p>)
    }
  }

  // Render one of the many parameter types that are specific to a particular module
  render_custom_parameter () {
    const { id_name, name } = this.props.p.parameter_spec

    switch (id_name) {
      case 'version_select':
        return (
          <div {...this.outerDivProps}>
            <VersionSelect
              name={name}
              onSubmit={this.props.onSubmit}
              wfModuleId={this.props.wfModuleId}
              wfModuleStatus={this.props.wfModuleStatus}
              isReadOnly={this.props.isReadOnly}
            />
          </div>
        )
      case 'version_select_simpler':
        return (
          <div className='versionSelect--uploadFile'>
            <DataVersionSelect wfModuleId={this.props.wfModuleId}/>
          </div>
        );
      case 'file':
        return (
          <DropZone
            wfModuleId={this.props.wfModuleId}
            lastRelevantDeltaId={this.props.lastRelevantDeltaId}
            api={this.props.api}
          />
        )
      case 'googlefileselect':
        const secret = this.props.getParamText('google_credentials')
        const secretName = secret ? (secret.name || null) : null
        return (
          <GoogleFileSelect
            api={this.props.api}
            isReadOnly={this.props.isReadOnly}
            googleCredentialsParamId={this.props.getParamId('google_credentials')}
            googleCredentialsSecretName={secretName}
            fileMetadataJson={this.props.getParamText('googlefileselect')}
            onChangeJson={this.onChangeGoogleFileSelectJson}
          />
        )
      case 'code':
        return (
          <LazyAceEditor
            name={this.props.p.parameter_spec.name}
            isZenMode={this.props.isZenMode}
            wfModuleError={this.props.wfModuleError}
            save={this.paramChanged}
            defaultValue={this.props.p.value}
          />
        )
      case 'celledits':
        return (
          <CellEditor
            edits={this.props.p.value}
            onSave={this.paramChanged}
          />
        )
      case 'refine':
        return (
          <Refine
            fetchData={this.getInputValueCounts}
            fetchDataCacheId={`${this.props.inputDeltaId}-${this.props.getParamText('column')}`}
            value={this.props.p.value}
            onChange={this.paramChanged}
          />
        )
      case 'reorder-history':
        return (
          <ReorderHistory
            history={this.props.getParamText('reorder-history')}
          />
        )
      case 'rename-entries':
        return (
          <RenameEntries
            wfModuleId={this.props.wfModuleId}
            isReadOnly={this.props.isReadOnly}
            entriesJsonString={this.props.p.value}
            allColumns={this.props.inputColumns}
            onChange={this.paramChanged}
          />
        )
      case 'y_columns':
        return (
          <ChartSeriesMultiSelect
            prompt='Select a numeric column'
            isReadOnly={this.props.isReadOnly}
            allColumns={this.props.inputColumns}
            series={JSON.parse(this.props.p.value || '[]')}
            onChange={this.onChangeYColumns}
            name={id_name}
          />
        )
//      case 'map-geojson':
//        return (
//          <MapLocationDropZone
//            api={this.props.api}
//            name={this.props.p.parameter_spec.name}
//            paramData={this.props.p.value}
//            paramId={this.props.p.id}
//            isReadOnly={this.props.isReadOnly}
//          />
//        )
//      case 'map-presets':
//        return (
//          <MapLocationPresets
//            api={this.props.api}
//            name={this.props.p.parameter_spec.name}
//            paramData={this.props.p.value}
//            paramId={this.props.p.id}
//            isReadOnly={this.props.isReadOnly}
//          />
//        )
//      case 'map-layers':
//        return (
//          <MapLayerEditor
//            api={this.props.api}
//            name={this.props.p.parameter_spec.name}
//            paramId={this.props.p.id}
//            keyColumn={this.props.getParamText("key-column")}
//            wfModuleId={this.props.wf_module_id}
//            isReadOnly={this.props.isReadOnly}
//            paramData={this.props.p.value}
//          />
//        )
      default:
        return (
          <p className="error">Custom type {id_name} not handled</p>
        )
    }
  }

  displayConditionalUI(condition) {
    // Checks if a menu item in the visibility condition is selected
    // If yes, display or hide the item depending on whether we have inverted the visibility condition
    // type is either 'visible_if' or 'visible_if_not'
    const invert = condition['invert'] === true

    if ('id_name' in condition && 'value' in condition) {
      const value = this.props.getParamText(condition['id_name']);

      // If the condition value is a boolean:
      if (typeof condition['value'] === typeof true || typeof condition['value'] === typeof 0) {
        let match
        if (value === condition['value']) {
          // Just return if it matches
          match = true
        } else if (typeof condition['value'] === typeof true && typeof value !== typeof true) {
          // If value: true or value: false, return whether string is set
          match = condition['value'] === (value !== '')
        } else {
          match = false
        }
        return invert !== match
      }

      // Otherwise, if it's a menu item:
      const condValues = condition['value'].split('|').map(cond => cond.trim())
      const selectionIdx = parseInt(value)
      if (!isNaN(selectionIdx)) {
        const menuItems = this.props.getParamMenuItems(condition['id_name'])
        if (menuItems.length > selectionIdx) {
          const selection = menuItems[selectionIdx]
          const selectionInCondition = (condValues.indexOf(selection) >= 0)
          return invert !== selectionInCondition
        }
      }
    }

    // If the visibility condition is empty or invalid, default to showing the parameter
    return true
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
        if (this.props.p.parameter_spec.multiline) {
          return (
            <div {...this.outerDivProps}>
              <div className='label-margin t-d-gray content-3'>{name}</div>
              <textarea
                onBlur={this.blur}
                readOnly={this.props.isReadOnly}
                className='module-parameter t-d-gray content-3 text-field-large'
                name={id_name}
                rows={4}
                defaultValue={this.props.p.value}
                placeholder={this.props.p.parameter_spec.placeholder || ''}
              />
            </div>
          )
        } else {
          return (
            <div {...this.outerDivProps}>
              <div className='label-margin t-d-gray content-3'>{name}</div>
              <SingleLineTextField
                isReadOnly={this.props.isReadOnly}
                onSubmit={this.onSubmit}
                onChange={this.onChange}
                onReset={this.onReset}
                placeholder={this.props.p.parameter_spec.placeholder || ''}
                name={id_name}
                initialValue={this.props.p.value}
                value={this.props.value}
              />
            </div>
          )
        }

      case 'integer':
      case 'float':
        return (
          <div {...this.outerDivProps}>
            <div className='label-margin t-d-gray content-3'>{name}</div>
            <NumberField
              isReadOnly={this.props.isReadOnly}
              onChange={this.onChange}
              onSubmit={this.onSubmit}
              onReset={this.onReset}
              initialValue={this.props.p.value}
              value={this.props.value}
              placeholder={this.props.p.parameter_spec.placeholder || ''}
            />
          </div>
        );

      case 'button':
        return (
          <div {...this.outerDivProps} className={this.paramClassName + ' d-flex justify-content-end'}>
            <button className='action-button button-blue' onClick={this.props.readOnly ? null : this.props.onSubmit}>{name}</button>
          </div>
        );
      case 'statictext':
        return (
          <div {...this.outerDivProps} className={this.paramClassName + ' t-m-gray info-2'}>{name}</div>
        );

      case 'checkbox':
        return (
          <div {...this.outerDivProps} className={this.paramClassName + ' checkbox-wrapper'}>
              <input
                disabled={this.props.isReadOnly}
                type="checkbox" className="checkbox"
                checked={this.props.p.value}
                onChange={this.onClickCheckbox}
                name={id_name}
                ref={ el => this.checkboxRef = el}
                id={this.props.p.id} />
              <label htmlFor={this.props.p.id}>{name}</label>
          </div>
        );
      case 'radio':
        return (
          <div {...this.outerDivProps}>
            <div className='d-flex align-items-center'>{name}</div>
            <RadioParam
              name={id_name}
              items={this.props.p.items}
              selectedIdx={this.props.p.value}
              isReadOnly={this.props.isReadOnly}
              onChange={this.paramChanged}
            />
          </div> );
      case 'menu':
        return (
          <div {...this.outerDivProps}>
            <div className='label-margin t-d-gray content-3'>{name}</div>
            <MenuParam
              name={id_name}
              items={this.props.p.items}
              selectedIdx={parseInt(this.props.p.value)}
              isReadOnly={this.props.isReadOnly}
              onChange={this.paramChanged}
            />
          </div> );
      case 'column':
        return (
          <div {...this.outerDivProps}>
            <div className='label-margin t-d-gray content-3'>{name}</div>
            <ColumnParam
              value={this.props.p.value}
              name={id_name}
              prompt={this.props.p.parameter_spec.placeholder}
              isReadOnly={this.props.isReadOnly}
              allColumns={this.props.inputColumns}
              onChange={this.paramChanged}
            />
          </div>
        )

      case 'multicolumn':
        // There's no good reason why we read/write `colnames` instead of our own
        // id_name. But it'll be a chore to change it: we'll need to change all modules'
        // id_name to `colnames` so that pre-chore data will migrate over.
        //
        // (Then we'll have one more chore: select JSON instead of comma-separated strings)
        return (
          <div {...this.outerDivProps}>
            <div className='t-d-gray content-3 label-margin'>{name}</div>
            <ColumnSelector
              name={id_name}
              isReadOnly={this.props.isReadOnly}
              value={this.props.getParamText('colnames')}
              allColumns={this.props.inputColumns}
              onChange={this.onColumnSelectorChange}
            />
          </div>
        )

      case 'secret':
        return this.render_secret_parameter();

      case 'custom':
        return this.render_custom_parameter();

      default:
        return null;  // unrecognized parameter type
    }
  }
}
