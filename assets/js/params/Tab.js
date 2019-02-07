import React from 'react'
import PropTypes from 'prop-types'
import Select from 'react-select'
import { MaybeLabel } from './util'

export const ReactSelectStyles = {
  control: () => ({})
}

export default class TabParam extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func(tabSlugOrEmptyString) => undefined
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    value: PropTypes.string.isRequired, // tab-slug, or ''
    upstreamValue: PropTypes.string.isRequired, // tab-slug, or ''
    placeholder: PropTypes.string, // default 'Select Tab'
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired
    }).isRequired).isRequired
  }

  onChange = (ev) => {
    this.props.onChange(ev.value || '')
  }

  render () {
    const { name, value, upstreamValue, placeholder, isReadOnly, fieldId, label, tabs } = this.props

    const tabOptions = tabs.map(({ slug, name }) => ({ label: name, value: slug }))
    const selectedOption = tabOptions.find(t => t.value === value)

    return (
      <React.Fragment>
        <MaybeLabel fieldId={fieldId} label={label} />
        <Select
          name={name}
          key={upstreamValue}
          inputId={fieldId}
          options={tabOptions}
          value={selectedOption}
          className='react-select tab'
          classNamePrefix='react-select'
          styles={ReactSelectStyles}
          menuPortalTarget={document.body}
          onChange={this.onChange}
          isClearable={false}
          isDisabled={isReadOnly}
          placeholder={placeholder || 'Select Tab'}
        />
      </React.Fragment>
    )
  }
}
