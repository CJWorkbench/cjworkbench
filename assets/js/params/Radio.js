// Simple wrapper over HTML <select>
import React from 'react'
import PropTypes from 'prop-types'

export default class RadioParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    items: PropTypes.string,  // like 'Apple|Banana|Kitten' ... DEPRECATED: prefer `options`
    options: PropTypes.arrayOf(PropTypes.shape({
      value: PropTypes.any.isRequired,
      label: PropTypes.string.isRequired,
    }).isRequired), // should be .isRequired).isRequired, but for now we accept .items instead
    value: PropTypes.any.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired // onChange(newIndex) => undefined
  }

  onChange = (ev) => {
    // <input value=...> is always a String. Our <option> values aren't.
    // Find the option matching the string, and return it.
    const strValue = ev.target.value
    const option = this.options.find(({ value }) => String(value) === strValue)
    this.props.onChange(option.value)
  }

  get options () {
    const { options, items } = this.props
    if (options) return options

    // Handle deprecated `this.props.items`
    return items.split('|').map((label, value) => ({ label, value })) // `value` is int array index
  }

  render() {
    const { items, name, fieldId, isReadOnly, value } = this.props
    const selectedValue = value
    const optionComponents = this.options.map(({ value, label }, i) => (
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
      <div className='button-group'>
        {optionComponents}
      </div>
    )
  }
}
