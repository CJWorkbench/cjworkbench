import React from 'react'
import PropTypes from 'prop-types'

/**
 * A text field for numbers.
 *
 * It has a submit button that appears when the value has changed.
 *
 * This field maintains no state. Its parent component must maintain its
 * `initialValue` (the value before edits) and `value` (the value it sends in
 * `onChange(value)`). It will call `onSubmit()` when the user presses Enter
 * or clicks its submit button; at that point the parent should do something
 * with the last-given `onChange(value)`.
 */
export default class NumberField extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // onChange(n) => undefined
    onSubmit: PropTypes.func.isRequired, // onSubmit() => undefined
    onReset: PropTypes.func.isRequired, // onReset() => undefined
    value: PropTypes.number, // maybe 0/null
    initialValue: PropTypes.number, // maybe 0/null
    placeholder: PropTypes.string // maybe empty
  }

  onChange = (ev) => {
    const value = Number(ev.target.value)
    this.props.onChange(value)
  }

  onKeyDown = (ev) => {
    switch (ev.keyCode) {
      case 13: // Enter
        ev.preventDefault()
        return this.props.onSubmit()
      case 27: // Escape
        ev.preventDefault()
        this.props.onReset()
      // else handle the key as usual
    }
  }

  render () {
    const { name, initialValue, value, placeholder, isReadOnly } = this.props
    const maybeButton = initialValue === value ? null : (
      <button title='submit' ref={this.buttonRef} onClick={this.props.onSubmit}>
        <i className='icon-caret-right' />
      </button>
    )

    return (
      <div className='number-field'>
        <input
          type='number'
          name={name}
          placeholder={placeholder}
          readOnly={isReadOnly}
          onChange={this.onChange}
          onKeyDown={this.onKeyDown}
          value={value}
        />
        {maybeButton}
      </div>
    )
  }
}
