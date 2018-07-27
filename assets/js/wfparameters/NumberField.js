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
export default class NumberField {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // onChange(n) => undefined
    onSubmit: PropTypes.func.isRequired, // onSubmit() => undefined
    value: PropTypes.number, // maybe 0/null
    initialValue: PropTypes.number, // maybe 0/null
    placeholder: PropTypes.string // maybe empty
  }
}
