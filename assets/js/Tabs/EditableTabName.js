import React from 'react'
import PropTypes from 'prop-types'

export default class EditableTabName extends React.PureComponent {
  static propTypes = {
    value: PropTypes.string.isRequired,
    isEditing: PropTypes.bool.isRequired,
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

  onChange = (ev) => {
    this.setState({ value: ev.target.value })
  }

  onKeyDown = (ev) => {
    switch (ev.key) {
      case 'Enter':
        this.props.onSubmit(this.state.value)
        this.setState({ value: null }) // for onBlur()
        return
      case 'Escape':
        this.setState({ value: null }) // for onBlur()
        this.props.onCancel()
        return
    }
  }

  onBlur = () => {
    // If 'Escape' was handled, `value` will be null _within setState()_.
    this.setState(({ value }) => {
      if (value === null) return // we already called this.props.onCancel()

      this.props.onSubmit(this.state.value)
    })
  }

  render () {
    const value = this.state.value === null ? this.props.value : this.state.value

    return (
      <input
        name='tab-name'
        value={value}
        onChange={this.onChange}
        onKeyDown={this.onKeyDown}
        onBlur={this.onBlur}
      />
    )
  }
}
