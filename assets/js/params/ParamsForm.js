import React from 'react'
import PropTypes from 'prop-types'
import Param from './Param'
import ParamsFormFooter from './ParamsFormFooter'
import deepEqual from 'fast-deep-equal'
import { paramFieldToParamProps } from './util'

/**
 * Displays Params and user's "edits".
 */
export default class ParamsForm extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    isZenMode: PropTypes.bool.isRequired,
    api: PropTypes.shape({ // We should nix this. Try to remove its properties, one by one....:
      createOauthAccessToken: PropTypes.func.isRequired, // for secrets
      valueCounts: PropTypes.func.isRequired // for ValueFilter/Refine
    }),
    fields: PropTypes.arrayOf(PropTypes.shape({
      idName: PropTypes.string.isRequired,
      name: PropTypes.string, // or null or ''
      type: PropTypes.string.isRequired,
      enumOptions: PropTypes.arrayOf(
        PropTypes.oneOfType([
          PropTypes.oneOf(['separator']), // menu only
          PropTypes.shape({
            value: PropTypes.any.isRequired,
            label: PropTypes.string.isRequired
          }).isRequired // menu or radio
        ]).isRequired
      ), // only set on menu/radio
      multiline: PropTypes.bool, // required for String
      placeholder: PropTypes.string, // required for many
      visibleIf: PropTypes.object, // JSON spec or null,
      childParameters: PropTypes.array,
      childDefault: PropTypes.object
    }).isRequired).isRequired,
    files: PropTypes.arrayOf(PropTypes.shape({
      uuid: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      size: PropTypes.number.isRequired,
      createdAt: PropTypes.string.isRequired // ISO-8601
    }).isRequired).isRequired,
    value: PropTypes.object, // upstream value. `null` if the server hasn't been contacted; otherwise, there's a key per field
    secrets: PropTypes.object, // upstream secrets. `null` if the server hasn't been contacted; otherwise, keys set only when params are filled in
    edits: PropTypes.object.isRequired, // local edits, same keys as `value`
    workflowId: PropTypes.number.isRequired,
    wfModuleId: PropTypes.number, // `null` if the server hasn't been contacted; otherwise, ID
    wfModuleSlug: PropTypes.string, // should be .isRequired but WfModule.js does not handle placeholders yet
    wfModuleOutputErrors: PropTypes.arrayOf(PropTypes.string), // `null` if no wfModule, empty if no error
    isWfModuleBusy: PropTypes.bool.isRequired,
    inputWfModuleId: PropTypes.number, // or `null`
    inputDeltaId: PropTypes.number, // or `null` ... TODO nix by making 0 fields depend on it
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    }).isRequired),
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      outputColumns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      }).isRequired) // null while rendering
    }).isRequired).isRequired,
    currentTab: PropTypes.string.isRequired, // "tab-slug", never null
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
    startCreateSecret: PropTypes.func.isRequired, // func(idName) => undefined
    deleteSecret: PropTypes.func.isRequired, // func(idName) => undefined
    submitSecret: PropTypes.func.isRequired, // func(idName, secretString) => undefined
    onChange: PropTypes.func.isRequired, // func(newValues) => undefined
    onSubmit: PropTypes.func.isRequired // func() => undefined
  }

  handleKeyDown = (ev) => {
    if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) {
      ev.preventDefault() // in case it was already going to submit
      this.handleSubmit()
    }
  }

  handleSubmit = (maybeEv) => {
    if (maybeEv) {
      // it's an HTML submit event: don't spawn the default HTTP request
      maybeEv.preventDefault()
    }

    this.props.onSubmit()
  }

  handleChange = (fieldName, fieldValue) => {
    const { value, edits, onChange } = this.props

    if (deepEqual(fieldValue, edits[fieldName])) {
      // setting a value to itself
      return
    }

    const newEdits = {
      ...edits,
      [fieldName]: fieldValue
    }

    if (value !== null && deepEqual(value[fieldName], newEdits[fieldName])) {
      // setting a value to its upstream value: mark it "not editing"
      delete newEdits[fieldName] // if it exists
    }

    onChange(newEdits)
  }

  get isEditing () {
    return Object.keys(this.props.edits).length > 0
  }

  /**
   * Flip name meanings: this.value is _edited_ values.
   *
   * The parent sets our `value` and `edits` prop. _We_ set our `Param`
   * childrens' values as `upstreamValue` (redux state) and `value`
   * (WfModule state).
   */
  get value () {
    if (this.props.value === null) return this.props.value
    if (!this.isEditing) return this.props.value // instead of creating a new object
    return {
      ...this.props.value,
      ...this.props.edits
    }
  }

  isFieldVersionSelect = ({ type, idName }) => {
    return type === 'custom' && (idName === 'version_select' || idName === 'version_select_simpler')
  }

  isFieldVisible = (field, recurseDetector = []) => {
    // No visibility condition, we are visible
    const condition = field.visibleIf
    if (!condition) return true

    const invert = !!condition.invert

    // missing idName, default to visible
    if (!condition.idName) return true

    // We are invisible if we depend upon an invisible field
    if (recurseDetector.indexOf(condition.idName) !== -1) {
      // Prevent infinite recursion; log to console instead.
      //
      // It's easier to _hide_ a broken field than _show_ it: hiding exits the
      // recursion and showing doesn't.
      console.warn(`Field ${field.idName} visibleIf depends on the field's own visibility. Please remove this recursive loop.`)
      return false
    }
    const conditionField = this.props.fields.find(f => f.idName === condition.idName)
    // Recurse to see if we depend on an invisible field
    if (!this.isFieldVisible(conditionField, [...recurseDetector, field.idName])) {
      return false
    }

    if ('value' in condition) {
      const value = this.value[condition.idName]

      // If the condition value is a boolean:
      if (typeof condition.value === 'boolean' || typeof condition.value === 'number') {
        let match
        if (value === condition.value) {
          // Just return if it matches
          match = true
        } else if (typeof condition.value === 'boolean' && typeof value !== 'boolean') {
          // Test for _truthiness_, not truth.
          match = condition.value === (!!value)
        } else {
          match = false
        }
        return invert !== match
      }

      // If it's a menu entry...
      if (
        (conditionField.type === 'menu' || conditionField.type === 'radio') &&
        Array.isArray(condition.value)
      ) {
        return invert !== condition.value.includes(value)
      }

      // ... the ideal is for this to be the _only_ code path. But there are
      // exceptions because the feature was implemented piecemeal
      return invert !== deepEqual(condition.value, value)
    }

    // If the visibility condition is empty or invalid, default to showing the parameter
    return true
  }

  render () {
    const {
      api, isReadOnly, isZenMode, workflowId, wfModuleId, wfModuleSlug, wfModuleOutputErrors, isWfModuleBusy,
      inputWfModuleId, inputDeltaId, inputColumns, tabs, currentTab, applyQuickFix,
      startCreateSecret, deleteSecret, submitSecret, fields, files, secrets
    } = this.props
    const isEditing = this.isEditing

    const upstreamValue = this.props.value
    const value = this.value

    // TODO Revamp Refine and ValueFilter so the select-column and edit-value components
    // are nested together. Until then, we need to pass `selectedColumn` to the edit-value
    // components so they can load data.
    const columnParam = fields.find(f => f.type === 'column')
    const selectedColumn = (columnParam && value && value[columnParam.idName]) || null
    // TODO ditto JoinColumns
    const tabParam = fields.find(f => f.type === 'tab')
    const selectedTab = (tabParam && value && value[tabParam.idName]) || null

    let className = 'module-card-params'
    if (isEditing) className += ' editing'

    const visibleFields = fields
      .filter(f => !this.isFieldVersionSelect(f))
      .filter(f => this.isFieldVisible(f))

    return (
      <form
        className={className}
        action=''
        onSubmit={this.handleSubmit}
        onKeyDown={this.handleKeyDown}
      >
        <div className='params'>
          {visibleFields.map(field => {
            let secretMetadata = null
            if (field.type === 'secret' && secrets) {
              secretMetadata = secrets[field.idName] || null
            } else if (field.secretParameter && secrets) {
              secretMetadata = secrets[field.secretParameter] || null
            }

            return (
              <Param
                api={api}
                isReadOnly={isReadOnly}
                isZenMode={isZenMode}
                key={field.idName}
                {...paramFieldToParamProps(field)}
                upstreamValue={upstreamValue ? upstreamValue[field.idName] : null}
                secretMetadata={secretMetadata}
                value={value ? value[field.idName] : null}
                files={files}
                workflowId={workflowId}
                wfModuleId={wfModuleId}
                wfModuleSlug={wfModuleSlug}
                wfModuleOutputErrors={wfModuleOutputErrors}
                isWfModuleBusy={isWfModuleBusy}
                inputWfModuleId={inputWfModuleId}
                inputDeltaId={inputDeltaId}
                inputColumns={inputColumns}
                tabs={tabs}
                currentTab={currentTab}
                applyQuickFix={applyQuickFix}
                startCreateSecret={startCreateSecret}
                deleteSecret={deleteSecret}
                submitSecret={submitSecret}
                selectedColumn={selectedColumn}
                selectedTab={selectedTab}
                onChange={this.handleChange}
                onSubmit={this.handleSubmit}
              />
            )
          })}
        </div>
        <ParamsFormFooter
          wfModuleId={wfModuleId}
          isWfModuleBusy={isWfModuleBusy}
          isEditing={isEditing}
          isReadOnly={isReadOnly}
          fields={fields}
        />
      </form>
    )
  }
}
