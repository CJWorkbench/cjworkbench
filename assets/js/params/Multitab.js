import React from 'react'
import PropTypes from 'prop-types'
import Select from 'react-select'
import { MaybeLabel } from './util'

export const ReactSelectStyles = {
  control: () => ({})
}

export default class MultitabParam extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func(['tab-1', 'tab-2']) => undefined
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    value: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // ['tab-slug', ...] or []
    upstreamValue: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // ['tab-slug', ...] or []
    placeholder: PropTypes.string, // default 'Select Tab'
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired
    }).isRequired).isRequired
  }

  onChange = (rawValues) => {
    const values = rawValues.map(({ value }) => value)
    this.props.onChange(values)
  }

  render () {
    const { name, value, upstreamValue, placeholder, isReadOnly, fieldId, label, tabs } = this.props

    const tabOptions = tabs.map(({ slug, name }) => ({ label: name, value: slug }))
    const selectedOptions = tabOptions.filter(t => value.includes(t.value))

    return (
      <React.Fragment>
        <MaybeLabel fieldId={fieldId} label={label} />
        <Select
          name={name}
          key={upstreamValue.join('|')}
          inputId={fieldId}
          options={tabOptions}
          value={selectedOptions}
          className='react-select multitab'
          classNamePrefix='react-select'
          styles={ReactSelectStyles}
          menuPortalTarget={document.body}
          onChange={this.onChange}
          isClearable={false}
          isDisabled={isReadOnly}
          placeholder={placeholder || 'Select Tabs'}
          isMulti
        />
      </React.Fragment>
    )
  }
}
