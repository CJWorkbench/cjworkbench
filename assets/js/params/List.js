import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from './util'

/**
 * A parameter that repeats a set of parameters
 */
export default class List extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    label: PropTypes.string.isRequired,
    fieldId: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired, // func(str) => undefined
    onSubmit: PropTypes.func.isRequired, // func() => undefined
    name: PropTypes.string.isRequired,
    upstreamValue: PropTypes.object, // sometimes empty string
    value: PropTypes.object,
  }

  onChange = (ev) => {
    // Remove newlines. We simply won't let this input produce one.
    const value = ev.target.value.replace(/[\r\n]/g, '')
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
    }
    // else handle the key as usual
  }

  render () {
    const { name, fieldId, label, upstreamValue, value, placeholder, isReadOnly } = this.props

    return (
      <React.Fragment>
        <h2>Array size is {Object.keys(this.props.value).length} yeah</h2>
      </React.Fragment>
    )
  }
}
