import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from './util'

/**
 * A text field for numbers.
 *
 * It has a submit button that appears when the value has changed.
 *
 * This field maintains no state. Its parent component must maintain its
 * `upstreamValue` (the value before edits) and `value` (the value it sends in
 * `onChange(value)`).
 */
export default class NumberField extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // onChange(n) => undefined
    onSubmit: PropTypes.func.isRequired, // onSubmit() => undefined
    value: PropTypes.number, // maybe 0/null
    upstreamValue: PropTypes.number, // maybe 0/null
    placeholder: PropTypes.string // maybe empty
  }

  onChange = (ev) => {
    const value = ev.target.value === '' ? null : Number(ev.target.value)
    this.props.onChange(value)
  }

  onKeyDown = (ev) => {
    switch (ev.key) {
      case 'Escape':
        ev.preventDefault()
        return this.props.onChange(this.props.upstreamValue)
      case 'Enter':
        ev.preventDefault()
        return this.props.onSubmit()
      // else handle the key as usual
    }
  }

  render () {
    const { name, value, label, fieldId, placeholder, isReadOnly } = this.props

    return (
      <React.Fragment>
        <MaybeLabel label={label} fieldId={fieldId} />
        <input
          type='number'
          name={name}
          id={fieldId}
          placeholder={placeholder}
          readOnly={isReadOnly}
          onChange={this.onChange}
          onKeyDown={this.onKeyDown}
          value={value}
        />
      </React.Fragment>
    )
  }
}
