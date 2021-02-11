import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from '../util'

/**
 * A text field for single-line text that ... wraps! Yay!
 *
 * It grows to fit its contents.
 *
 * This field maintains no state. Its parent component must maintain its
 * `upstreamValue` (the value before edits) and `value` (the value it sends in
 * `onChange(value)`).
 */
export default class SingleLineString extends PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    label: PropTypes.string.isRequired,
    fieldId: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired, // func(str) => undefined
    onSubmit: PropTypes.func.isRequired, // func() => undefined
    name: PropTypes.string.isRequired,
    upstreamValue: PropTypes.string, // sometimes empty string
    value: PropTypes.string, // sometimes empty string
    placeholder: PropTypes.string // sometimes empty string
  }

  handleChange = ev => {
    // Remove newlines. We simply won't let this input produce one.
    const value = ev.target.value.replace(/[\r\n]/g, '')
    this.props.onChange(value)
  }

  handleKeyDown = ev => {
    switch (ev.key) {
      case 'Escape':
        ev.preventDefault()
        return this.props.onChange(this.props.upstreamValue)
      case 'Enter':
        ev.preventDefault()
        return this.props.onSubmit()
    }
    // else handle the key as usual
  }

  render () {
    const { name, fieldId, label, value, placeholder, isReadOnly } = this.props

    return (
      <>
        <MaybeLabel fieldId={fieldId} label={label} />
        <div className='autosize'>
          <div className='invisible-size-setter'>{value}</div>
          <textarea
            readOnly={isReadOnly}
            name={name}
            id={fieldId}
            placeholder={placeholder}
            onChange={this.handleChange}
            onKeyDown={this.handleKeyDown}
            value={value}
          />
        </div>
      </>
    )
  }
}
