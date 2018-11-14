import React from 'react'
import PropTypes from 'prop-types'

/**
 * A text field for multiline text areas
 *
 * When the user enters new text, a submit button appears
 *
 * This field maintains no state. Its parent component must maintain its
 * `initialValue` (the value before edits) and `value` (the value it sends in
 * `onChange(value)`). It will call `onSubmit()` when the user presses Enter
 * or clicks its submit button; at that point the parent should do something
 * with the last-given `onChange(value)`.
 */
export default class MultiLineTextArea extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func(str) => undefined
    onSubmit: PropTypes.func.isRequired, // func() => undefined
    name: PropTypes.string.isRequired,
    initialValue: PropTypes.string, // sometimes empty string
    value: PropTypes.string, // sometimes empty string
    placeholder: PropTypes.string // sometimes empty string
  }

  onChange = (ev) => {
    this.props.onChange(ev.target.value)
  }

  render () {
    const { initialValue, value, placeholder, isReadOnly, name } = this.props
    const maybeButton = initialValue === value ? null : (
      <button title="submit" onClick={this.props.onSubmit}>
        <i className="icon-play" />
      </button>
    )
    return (
      <div className="text-field-large">
        <textarea
          onBlur={this.onChange}
          onChange={this.onChange}
          readOnly={isReadOnly}
          name={name}
          rows={4}
          defaultValue={value}
          placeholder={placeholder || ''}
        />
        {maybeButton}
      </div>
    )
  }
}
