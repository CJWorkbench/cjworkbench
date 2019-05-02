// Simple wrapper over HTML <select>
import React from 'react'
import PropTypes from 'prop-types'

export default class RadioParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    enumOptions: PropTypes.arrayOf(PropTypes.shape({
      value: PropTypes.any.isRequired,
      label: PropTypes.string.isRequired,
    }).isRequired).isRequired,
    value: PropTypes.any.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired // onChange(newIndex) => undefined
  }

  onChange = (ev) => {
    // <input value=...> is always a String. Our enumOptions values aren't.
    // Find the option matching the string, and return it.
    const { onChange, enumOptions } = this.props
    const strValue = ev.target.value
    const option = enumOptions.find(({ value }) => String(value) === strValue)
    onChange(option.value)
  }

  render() {
    const { enumOptions, name, fieldId, isReadOnly, value } = this.props
    const selectedValue = value
    const optionComponents = enumOptions.map(({ value, label }, i) => (
      <label key={i} className='t-d-gray content-1'>
        <input
          type='radio'
          name={`${name}`}
          id={`${fieldId}${i === 0 ? '' : ('_' + i)}`}
          className='radio-button'
          value={String(value)}
          checked={String(value) === String(selectedValue)}
          onChange={this.onChange}
          disabled={this.props.isReadOnly}
        />
        <span className="button"></span>
        {label}
      </label>
    ))

    return (
      <div className='radio-options'>
        {optionComponents}
      </div>
    )
  }
}
