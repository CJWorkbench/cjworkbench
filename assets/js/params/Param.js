import React from 'react'
import PropTypes from 'prop-types'
import { generateFieldId } from './util'
import Checkbox from './Checkbox'
import Column from './Column'
import Custom from './Custom'
import deepEqual from 'fast-deep-equal'
import Menu from './Menu'
import Multicolumn from './Multicolumn'
import Multitab from './Multitab'
import Multichartseries from './Multichartseries'
import Number_ from './Number'
import Radio from './Radio'
import Secret from './Secret'
import StaticText from './StaticText'
import String_ from './String'
import Tab from './Tab'

export default class Param extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    isZenMode: PropTypes.bool.isRequired,
    api: PropTypes.shape({ // We should nix this. Try to remove its properties, one by one....:
      createOauthAccessToken: PropTypes.func.isRequired, // for secrets
      valueCounts: PropTypes.func.isRequired, // for ValueFilter/Refine
      _fetch: PropTypes.func.isRequired, // for DropZone
    }),
    name: PropTypes.string.isRequired,
    secretParamName: PropTypes.string, // or null: name of a 'secret'-typed param
    secretName: PropTypes.string, // or null: name of user logged in (if there is a secretParamName)
    label: PropTypes.string.isRequired, // or ''
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
    ), // new-style menu -- once we nix "items" ("menu_items" in spec), add .isRequired here
    isMultiline: PropTypes.bool.isRequired,
    placeholder: PropTypes.string.isRequired, // may be ''
    visibleIf: PropTypes.object, // JSON spec or null
    upstreamValue: PropTypes.any, // `null` if server hasn't been contacted or if actual value is `null`
    value: PropTypes.any, // local value: `null` if server hasn't been contacted or if actual value is `null`
    wfModuleId: PropTypes.number, // `null` if the server hasn't been contacted; otherwise, ID
    wfModuleOutputError: PropTypes.string, // `null` if no wfModule, '' if no error
    isWfModuleBusy: PropTypes.bool.isRequired,
    inputWfModuleId: PropTypes.number, // or `null`
    inputDeltaId: PropTypes.number, // or `null` ... TODO nix by making 0 fields depend on it
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf([ 'text', 'number', 'datetime' ]).isRequired
    }).isRequired), // null while rendering
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      outputColumns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf([ 'text', 'number', 'datetime' ]).isRequired
      }).isRequired) // null while rendering
    }).isRequired).isRequired,
    currentTab: PropTypes.string.isRequired, // "tab-slug" this form appears in
    selectedTab: PropTypes.string, // "tab-slug" of one "tab" param elsewhere in this form
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
    startCreateSecret: PropTypes.func.isRequired, // func(idName) => undefined
    deleteSecret: PropTypes.func.isRequired, // func(idName) => undefined
    onChange: PropTypes.func.isRequired, // func(idName, value) => undefined -- will set `value` in parent
    onSubmit: PropTypes.func.isRequired, // func() => undefined
  }

  get innerComponent () {
    const { type, isMultiline } = this.props
    switch (type) {
      case 'checkbox': return Checkbox
      case 'column': return Column
      case 'custom': return Custom
      case 'float': return Number_
      case 'integer': return Number_
      case 'menu': return Menu
      case 'multicolumn': return Multicolumn
      case 'multitab': return Multitab
      case 'multichartseries': return Multichartseries
      case 'radio': return Radio
      case 'secret': return Secret
      case 'statictext': return StaticText
      case 'string': return String_
      case 'tab': return Tab
    }
  }

  onChange = (value) => {
    const { name, onChange } = this.props
    onChange(name, value)
  }

  createOauthAccessToken = () => {
    const { secretParamName, wfModuleId, api } = this.props
    return api.createOauthAccessToken(wfModuleId, secretParamName)
  }

  render () {
    const { wfModuleId, name, type, label, value, upstreamValue } = this.props

    const fieldId = generateFieldId(wfModuleId, name)

    let className = `param param-${type}`
    // "custom" is a type that we should probably nix. Basically,
    // "type=custom, name=refine" behaves like "type=refine". Historically this
    // made sense (since types were enums in the database). [2019-01-09] today
    // it doesn't, really -- "type=refine" might be better.
    //
    // Add class name 'param-refine' when type=custom, name=refine. This will
    // aid with styling because when we add the `.editing` and the
    // `.param-refine` classes, Refine's CSS can select
    // `.param-refine.editing`. (If we'd put `.editing` _here_ but
    // `.param-refine` in Custom.scss, selectors would be ugly.)
    if (type === 'custom') className += ` param-${name}`

    // Add class name '.editing' when we are editing
    if (!deepEqual(value, upstreamValue)) className += ' editing'

    return (
      <div data-name={name} className={className}>
        <this.innerComponent
          {...this.props}
          fieldId={fieldId}
          createOauthAccessToken={this.createOauthAccessToken}
          onChange={this.onChange}
        />
      </div>
    )
  }
}
