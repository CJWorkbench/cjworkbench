// WfParameter - a single editable parameter

import React from 'react'
import PropTypes from 'prop-types'
import MenuParam from './wfparameters/MenuParam'
import ChartSeriesMultiSelect from './wfparameters/ChartSeriesMultiSelect'
import ColumnParam from './wfparameters/ColumnParam'
import Multicolumn from './wfparameters/Multicolumn'
import DataVersionSelect from './wfparameters/DataVersionSelect'
import LazyDropZone from './wfparameters/LazyDropZone'
import VersionSelect from './wfparameters/VersionSelect'
import OAuthConnect from './wfparameters/OAuthConnect'
import GoogleFileSelect from './wfparameters/GoogleFileSelect'
import LazyAceEditor from './wfparameters/LazyAceEditor'
import CellEditor from './wfparameters/CellEditor'
import NumberField from './wfparameters/NumberField'
import Refine from './wfparameters/Refine'
import ReorderHistory from './wfparameters/ReorderHistory'
import Aggregations from './wfparameters/Aggregations'
import Groups from './wfparameters/Groups'
import RenameEntries from './wfparameters/RenameEntries'
import SingleLineTextField from './wfparameters/SingleLineTextField'
import RadioParam from './wfparameters/RadioParam'
import MultiLineTextArea from './wfparameters/MultiLineTextArea'
import ValueSelect from './wfparameters/ValueSelect'

export default class WfParameter extends React.PureComponent {
  static propTypes = {
    idName: PropTypes.string.isRequired, // slug
    name: PropTypes.string.isRequired, // user-visible
    multiline: PropTypes.bool, // null if non-string
    placeholder: PropTypes.string, // optional
    type: PropTypes.oneOf([
      'string',
      'integer',
      'float',
      'button',
      'statictext',
      'checkbox',
      'radio',
      'menu',
      'column',
      'multicolumn',
      'secret',
      'custom'
    ]).isRequired,
    items: PropTypes.string, // for menu/radio params: 'item1|item2|item3'
    initialValue: PropTypes.any, // initial value -- value in Redux store
    deleteSecret: PropTypes.func.isRequired, // func(paramIdName) => undefined
    startCreateSecret: PropTypes.func.isRequired, // func(paramIdName) => undefined
    wfModuleStatus: PropTypes.string, // module status, or null for placeholder
    wfModuleOutputError:  PropTypes.string, // module-level error message
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
    setWfModuleParams: PropTypes.func, // func(wfModuleId, { paramidname: newVal }) => undefined -- icky, prefer onChange
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
    getParamText:   PropTypes.func.isRequired,
    // "new-style" API: what it should have been all along. Normal React state stuff.
    onChange: PropTypes.func.isRequired, // func(idName, newValue) => undefined
    onSubmit: PropTypes.func.isRequired, // func() => undefined
    onReset: PropTypes.func.isRequired, // func(idName) => undefined
    value: PropTypes.any // value user has edited but not saved -- usually initialValue, empty is allowed
  }

  createGoogleOauthAccessToken = () => {
    const { api, wfModuleId } = this.props
    return api.createOauthAccessToken(wfModuleId, 'google_credentials')
  }

  get outerDivProps() {
    const { idName } = this.props

    return {
      className: this.paramClassName,
      'data-name': idName, // super-useful when inspecting -- e.g., when developing lessons
    }
  }

  get paramClassName() {
    const { idName, type } = this.props

    const nameParts = idName.split('|')[0].split('.').slice(1)

    nameParts.unshift(`wf-parameter-${type}`)
    nameParts.unshift('wf-parameter')

    return nameParts.join(' ')
  }

  onChange = (value) => {
    this.props.onChange(this.props.idName, value)
  }

  onSubmit = () => {
    this.props.onSubmit()
  }

  onReset = () => {
    this.props.onReset(this.props.idName)
  }

  paramChanged = (value) => {
    this.props.setWfModuleParams({ [this.props.idName]: value })
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
    const { onChange, onSubmit, idName } = this.props
    onChange(idName, json)
    onSubmit()
  }

  onChangeYColumns = (arr) => {
    const { setWfModuleParams, idName } = this.props
    setWfModuleParams({ [idName]: JSON.stringify(arr) })
  }

  render_secret_parameter() {
    const { value, idName, deleteSecret, startCreateSecret } = this.props
    const secretName = value ? (value.name || null) : null

    switch (idName) {
      case 'google_credentials':
      case 'twitter_credentials':
        return (
          <OAuthConnect
            paramIdName={idName}
            startCreateSecret={startCreateSecret}
            deleteSecret={deleteSecret}
            secretName={secretName}
          />
        )

     default:
       return (<p className="error">Secret type {idName} not handled</p>)
    }
  }

  // Render one of the many parameter types that are specific to a particular module
  render_custom_parameter () {
    const { idName, name, onSubmit, wfModuleId, wfModuleStatus, wfModuleOutputError,
            isReadOnly, isZenMode, value, initialValue, lastRelevantDeltaId, api,
            inputColumns, applyQuickFix } = this.props

    switch (idName) {
      case 'aggregations':
        return (
          <Aggregations
            isReadOnly={isReadOnly}
            name={idName}
            value={value}
            allColumns={inputColumns}
            onChange={this.paramChanged}
          />
        )
      case 'groups':
        return (
          <Groups
            isReadOnly={isReadOnly}
            name={idName}
            value={value}
            allColumns={inputColumns}
            onChange={this.paramChanged}
            applyQuickFix={applyQuickFix}
          />
        )
      case 'version_select':
        return (
          <div {...this.outerDivProps}>
            <VersionSelect
              name={name}
              onSubmit={onSubmit}
              wfModuleId={wfModuleId}
              wfModuleStatus={wfModuleStatus}
              isReadOnly={isReadOnly}
            />
          </div>
        )
      case 'version_select_simpler':
        return (
          <div className='versionSelect--uploadFile'>
            <DataVersionSelect wfModuleId={wfModuleId}/>
          </div>
        )
      case 'file':
        return (
          <LazyDropZone
            wfModuleId={wfModuleId}
            lastRelevantDeltaId={lastRelevantDeltaId}
            api={api}
          />
        )
      case 'googlefileselect':
        const secret = this.props.getParamText('google_credentials')
        const secretName = secret ? (secret.name || null) : null
        return (
          <GoogleFileSelect
            createOauthAccessToken={this.createGoogleOauthAccessToken}
            isReadOnly={isReadOnly}
            googleCredentialsSecretName={secretName}
            fileMetadataJson={value}
            onChangeJson={this.onChangeGoogleFileSelectJson}
          />
        )
      case 'code':
        return (
          <LazyAceEditor
            name={name}
            isZenMode={isZenMode}
            wfModuleError={wfModuleOutputError}
            save={this.paramChanged}
            defaultValue={value}
          />
        )
      case 'celledits':
        return (
          <CellEditor
            edits={value}
            onSave={this.paramChanged}
          />
        )
      case 'refine':
        return (
          <Refine
            fetchData={this.getInputValueCounts}
            fetchDataCacheId={`${this.props.inputDeltaId}-${this.props.getParamText('column')}`}
            value={value}
            onChange={this.paramChanged}
          />
        )
      case 'reorder-history':
        return (
          <ReorderHistory
            history={value}
          />
        )
      case 'rename-entries':
        return (
          <RenameEntries
            wfModuleId={wfModuleId}
            isReadOnly={isReadOnly}
            entriesJsonString={value}
            allColumns={inputColumns}
            onChange={this.paramChanged}
          />
        )
      case 'y_columns':
        return (
          <ChartSeriesMultiSelect
            prompt='Select a numeric column'
            isReadOnly={isReadOnly}
            allColumns={inputColumns}
            series={JSON.parse(value || '[]')}
            onChange={this.onChangeYColumns}
            name={idName}
          />
        )
      case 'valueselect':
        return (
          <ValueSelect
            fetchData={this.getInputValueCounts}
            fetchDataCacheId={`${this.props.inputDeltaId}-${this.props.getParamText('column')}`}
            value={value}
            onChange={this.paramChanged}
          />
        )
      default:
        return (
          <p className="error">Custom type {idName} not handled</p>
        )
    }
  }

  render() {
    const { idName, name, type, value, initialValue,
            multiline, isReadOnly, placeholder, items, inputColumns } = this.props

    switch (type) {
      case 'string':
        // Different size and style if it's a multiline string
        if (multiline) {
          return (
            <div {...this.outerDivProps}>
              <div className='parameter-label'>{name}</div>
              <MultiLineTextArea
                isReadOnly={isReadOnly}
                name={idName}
                value={value}
                initialValue={initialValue}
                onChange={this.onChange}
                onSubmit={this.onSubmit}
                placeholder={placeholder || ''}
              />
            </div>
          )
        } else {
          return (
            <div {...this.outerDivProps}>
              <div className='parameter-label'>{name}</div>
              <SingleLineTextField
                isReadOnly={isReadOnly}
                onSubmit={this.onSubmit}
                onChange={this.onChange}
                onReset={this.onReset}
                placeholder={placeholder || ''}
                name={idName}
                initialValue={initialValue}
                value={value}
              />
            </div>
          )
        }

      case 'integer':
      case 'float':
        return (
          <div {...this.outerDivProps}>
            <div className='parameter-label'>{name}</div>
            <NumberField
              isReadOnly={isReadOnly}
              onChange={this.onChange}
              onSubmit={this.onSubmit}
              onReset={this.onReset}
              initialValue={initialValue}
              value={value}
              placeholder={placeholder || ''}
            />
          </div>
        )

      case 'button':
        return (
          <div {...this.outerDivProps} className={this.paramClassName + ' d-flex justify-content-end'}>
            <button className='action-button button-blue' disabled={isReadOnly}>{name}</button>
          </div>
        )

      case 'statictext':
        return (
          <div {...this.outerDivProps} className={this.paramClassName + ' parameter-label'}>{name}</div>
        )

      case 'checkbox':
        const htmlId = `${idName}-${this.props.wfModuleId}`
        return (
          <div {...this.outerDivProps} className={this.paramClassName + ' checkbox-wrapper'}>
            <input
              disabled={isReadOnly}
              type="checkbox" className="checkbox"
              checked={value}
              onChange={this.onClickCheckbox}
              name={idName}
              id={htmlId}
            />
            <label htmlFor={htmlId}>{name}</label>
          </div>
        )
      case 'radio':
        return (
          <div {...this.outerDivProps}>
            <div className='d-flex align-items-center'>{name}</div>
            <RadioParam
              name={idName}
              items={items}
              selectedIdx={value}
              isReadOnly={isReadOnly}
              onChange={this.paramChanged}
            />
          </div>
        )
      case 'menu':
        return (
          <div {...this.outerDivProps}>
            <div className='parameter-label'>{name}</div>
            <MenuParam
              name={idName}
              items={items}
              selectedIdx={value}
              isReadOnly={isReadOnly}
              onChange={this.paramChanged}
            />
          </div>
        )
      case 'column':
        return (
          <div {...this.outerDivProps}>
            <div className='parameter-label'>{name}</div>
            <ColumnParam
              value={value}
              name={idName}
              prompt={placeholder || ''}
              isReadOnly={isReadOnly}
              allColumns={inputColumns}
              onChange={this.paramChanged}
            />
          </div>
        )

      case 'multicolumn':
        return (
          <div {...this.outerDivProps}>
            <div className='t-d-gray content-1 label-margin'>{name}</div>
            <Multicolumn
              name={idName}
              isReadOnly={isReadOnly}
              initialValue={initialValue}
              value={value}
              allColumns={inputColumns}
              onSubmit={this.onSubmit}
              onChange={this.onChange}
            />
          </div>
        )

      case 'secret':
        return this.render_secret_parameter()

      case 'custom':
        return this.render_custom_parameter()

      default:
        return null // unrecognized parameter type
    }
  }
}
