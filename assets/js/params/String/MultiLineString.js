import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from '../util'

/**
 * A text field for multiline text areas
 */
export default class MultiLineString extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func(str) => undefined
    name: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    fieldId: PropTypes.string.isRequired,
    value: PropTypes.string, // sometimes empty string
    placeholder: PropTypes.string // sometimes empty string
  }

  onChange = (ev) => {
    this.props.onChange(ev.target.value)
  }

  render () {
    const { fieldId, label, value, placeholder, isReadOnly, name } = this.props

    return (
      <>
        <MaybeLabel fieldId={fieldId} label={label} />
        <textarea
          onChange={this.onChange}
          readOnly={isReadOnly}
          id={fieldId}
          name={name}
          rows={4}
          value={value}
          placeholder={placeholder || ''}
        />
      </>
    )
  }
}
