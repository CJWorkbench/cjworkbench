import React from 'react'
import PropTypes from 'prop-types'
import Param from './Param'
import ParamsFormFooter from './ParamsFormFooter'
import deepEqual from 'fast-deep-equal'

/**
 * Displays Params and user's "edits".
 */
export default class ParamsForm extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    isZenMode: PropTypes.bool.isRequired,
    api: PropTypes.shape({ // We should nix this. Try to remove its properties, one by one....:
      createOauthAccessToken: PropTypes.func.isRequired, // for secrets
      valueCounts: PropTypes.func.isRequired, // for ValueFilter/Refine
      _fetch: PropTypes.func.isRequired, // for DropZone
    }),
    fields: PropTypes.arrayOf(PropTypes.shape({
      id_name: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired, // or null or ''
      type: PropTypes.string.isRequired,
      items: PropTypes.string, // "option0|option1|option2", null except when type=menu/radio
      enumOptions: PropTypes.arrayOf(
        PropTypes.oneOfType([
          PropTypes.oneOf([ 'separator' ]),
          PropTypes.shape({
            value: PropTypes.any.isRequired,
            label: PropTypes.string.isRequired
          }).isRequired
        ]).isRequired
      ), // new-style menu/radio -- once we nix "items" ("menu_items" in spec), add .isRequired here
      multiline: PropTypes.bool.isRequired,
      placeholder: PropTypes.string.isRequired, // may be ''
      visible_if: PropTypes.object // JSON spec or null
    }).isRequired).isRequired,
    value: PropTypes.object, // upstream value. `null` if the server hasn't been contacted; otherwise, there's a key per field
    edits: PropTypes.object.isRequired, // local edits, same keys as `value`
    wfModuleId: PropTypes.number, // `null` if the server hasn't been contacted; otherwise, ID
    wfModuleOutputError: PropTypes.string, // `null` if no wfModule, '' if no error
    isWfModuleBusy: PropTypes.bool.isRequired,
    inputWfModuleId: PropTypes.number, // or `null`
    inputDeltaId: PropTypes.number, // or `null` ... TODO nix by making 0 fields depend on it
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf([ 'text', 'number', 'datetime' ]).isRequired
    }).isRequired),
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      outputColumns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf([ 'text', 'number', 'datetime' ]).isRequired
      }).isRequired) // null while rendering
    }).isRequired).isRequired,
    currentTab: PropTypes.string.isRequired, // "tab-slug", never null
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
    startCreateSecret: PropTypes.func.isRequired, // func(idName) => undefined
    deleteSecret: PropTypes.func.isRequired, // func(idName) => undefined
    onChange: PropTypes.func.isRequired, // func(newValues) => undefined
    onSubmit: PropTypes.func.isRequired, // func() => undefined
  }

  onKeyDown = (ev) => {
    if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) {
      ev.preventDefault() // in case it was already going to submit
      this.onSubmit()
    }
  }

  onSubmit = (maybeEv) => {
    if (maybeEv) {
      // it's an HTML submit event: don't spawn the default HTTP request
      maybeEv.preventDefault()
    }

    this.props.onSubmit()
  }

  onChange = (fieldName, fieldValue) => {
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

  isFieldVersionSelect = ({ type, id_name }) => {
    return type === 'custom' && (id_name === 'version_select' || id_name === 'version_select_simpler')
  }

  isFieldVisible = (field) => {
    // No visibility condition, we are visible
    const condition = field.visible_if
    if (!condition) return true

    const invert = !!condition.invert

    // missing id_name, default to visible
    if (!condition.id_name) return true

    // We are invisible if our parent is invisible
    if (condition.id_name !== field.id_name) { // prevent simple infinite recurse; see droprowsbyposition.json
      const parentField = this.props.fields.find(f => f.id_name === condition.id_name)
      if (parentField && !this.isFieldVisible(parentField)) { // recurse
        return false
      }
    }

    if ('value' in condition) {
      const value = this.value[condition.id_name]

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

      // Otherwise, if it's a deprecated_menu item:
      const condField = this.props.fields.find(f => f.id_name === condition.id_name)
      if (condField.items) {
        // deprecated_menu field
        const condValues = condition.value.split('|').map(cond => cond.trim())
        const deprecatedMenuItems = condField.items.split('|').map(item => item.trim())
        if (deprecatedMenuItems.length > value) {
          const selection = deprecatedMenuItems[value]
          const selectionInCondition = (condValues.indexOf(selection) !== -1)
          return invert !== selectionInCondition
        }
      }

      // If it's a menu entry...
      if (Array.isArray(condition.value)) {
        return invert !== condition.value.includes(value)
      }

      // Menu entry (_not_ deprecated_menu), String...
      // ... the ideal is for this to be the _only_ code path. But there are
      // exceptions because the feature was implemented piecemeal
      return invert !== (condition.value === value)
    }

    // If the visibility condition is empty or invalid, default to showing the parameter
    return true
  }

  render () {
    const { api, isReadOnly, isZenMode, wfModuleId, wfModuleOutputError, isWfModuleBusy,
            inputWfModuleId, inputDeltaId, inputColumns, tabs, currentTab, applyQuickFix,
            startCreateSecret, deleteSecret, fields } = this.props
    const isEditing = this.isEditing

    const upstreamValue = this.props.value
    const value = this.value

    // TODO make secrets "special" -- not just a param type. Then we'll have something
    // sensible to pass components that use a secret (such as GoogleFileSelect). The
    // dream: the client manages wf_modules[id].params and wf_modules[id].secrets (just
    // like the server).
    //
    // In the meantime: find and pass `secretName` to all params if a secret is set.
    const secretParam = fields.find(f => f.type === 'secret')
    const secretParamName = secretParam ? secretParam.id_name : null
    const secretName = (secretParamName && value && value[secretParamName]) ? value[secretParamName].name : null

    // TODO Revamp Refine and ValueFilter so the select-column and edit-value components
    // are nested together. Until then, we need to pass `selectedColumn` to the edit-value
    // components so they can load data.
    const columnParam = fields.find(f => f.type === 'column')
    const selectedColumn = columnParam && value && value[columnParam.id_name] || null
    // TODO ditto JoinColumns
    const tabParam = fields.find(f => f.type === 'tab')
    const selectedTab = tabParam && value && value[tabParam.id_name] || null

    let className = 'module-card-params'
    if (isEditing) className += ' editing'

    const visibleFields = fields
      .filter(f => !this.isFieldVersionSelect(f))
      .filter(this.isFieldVisible)

    return (
      <form
        className={className}
        action=''
        onSubmit={this.onSubmit}
        onKeyDown={this.onKeyDown}
      >
        <div className='params'>
          {visibleFields.map(field => (
            <Param
              api={api}
              isReadOnly={isReadOnly}
              isZenMode={isZenMode}
              api={api}
              key={field.id_name}
              name={field.id_name}
              label={field.name}
              type={field.type}
              items={field.items}
              enumOptions={field.enumOptions}
              isMultiline={field.multiline || false}
              placeholder={field.placeholder || ''}
              visibleIf={field.visible_if || null}
              upstreamValue={upstreamValue ? upstreamValue[field.id_name] : null}
              value={value ? value[field.id_name] : null}
              wfModuleId={wfModuleId}
              wfModuleOutputError={wfModuleOutputError}
              isWfModuleBusy={isWfModuleBusy}
              inputWfModuleId={inputWfModuleId}
              inputDeltaId={inputDeltaId}
              inputColumns={inputColumns}
              tabs={tabs}
              currentTab={currentTab}
              applyQuickFix={applyQuickFix}
              secretName={secretName}
              secretParamName={secretParamName}
              startCreateSecret={startCreateSecret}
              deleteSecret={deleteSecret}
              selectedColumn={selectedColumn}
              selectedTab={selectedTab}
              onChange={this.onChange}
              onSubmit={this.onSubmit}
            />
          ))}
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
