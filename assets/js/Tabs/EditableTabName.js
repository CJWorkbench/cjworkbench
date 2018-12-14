import React from 'react'
import PropTypes from 'prop-types'

export default class EditableTabName extends React.PureComponent {
  static propTypes = {
    value: PropTypes.string.isRequired,
    isEditing: PropTypes.bool.isRequired,
    onClick: PropTypes.func.isRequired, // func() => undefined
    onSubmit: PropTypes.func.isRequired, // func(value) => undefined
    onCancel: PropTypes.func.isRequired, // func() => undefined
  }

  state = {
    value: null
  }

  renderInner () {
    const { value, isEditing } = this.props

    if (isEditing) {
      throw new Error('No edit feature yet')
    } else {
      return (
        <button className='tab-name' onClick={this.props.onClick}>{value}</button>
      )
    }
  }

  render () {
    return (
      <div className='tab-name'>
        {this.renderInner()}
      </div>
    )
  }
}
