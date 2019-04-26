import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from './util'

export default class MenuParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    enumOptions: PropTypes.arrayOf(
      PropTypes.oneOfType([
        PropTypes.oneOf([ 'separator' ]),
        PropTypes.shape({
          value: PropTypes.any.isRequired,
          label: PropTypes.string.isRequired
        }).isRequired
      ]).isRequired
    ).isRequired,
    value: PropTypes.oneOfType([
      PropTypes.number.isRequired, // DEPRECATED
      PropTypes.string.isRequired // new-style menu
    ]).isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired // onChange(newIndex) => undefined
  }

  onChange = (ev) => {
    const { enumOptions, onChange } = this.props

    // HTML <option> value is always String; find the _real_ value from
    // the String.
    const strValue = ev.target.value
    const value = enumOptions.find(({ value }) => String(value) === strValue).value

    onChange(value)
  }

  render() {
    const { items, name, fieldId, label, enumOptions, isReadOnly, value } = this.props

    const options = enumOptions.map((option, i) => {
      if (option === 'separator') {
        return <option disabled key={i} className='separator' />
      } else {
        // <option> value must always be String
        return <option key={option.value} value={String(option.value)}>{option.label}</option>
      }
    })

    return (
      <React.Fragment>
        <MaybeLabel fieldId={fieldId} label={label} />
        <select
          name={name}
          id={fieldId}
          value={String(value)}
          onChange={this.onChange}
          disabled={isReadOnly}
        >
          {options}
        </select>
      </React.Fragment>
    )
  }
}
