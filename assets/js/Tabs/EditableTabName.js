import React from 'react'
import PropTypes from 'prop-types'

export default class EditableTabName extends React.PureComponent {
  static propTypes = {
    value: PropTypes.string.isRequired,
    onSubmit: PropTypes.func.isRequired, // func(value) => undefined
    onCancel: PropTypes.func.isRequired, // func() => undefined
  }

  state = {
    value: null
  }

  inputRef = React.createRef()

  onChange = (ev) => {
    this.setState({ value: ev.target.value })
  }

  componentDidMount = () => {
    this.inputRef.current.focus()
  }

  onKeyDown = (ev) => {
    switch (ev.key) {
      case 'Enter':
        this.props.onSubmit(this.state.value)
        this.setState({ value: null }) // for onBlur()
        return
      case 'Escape':
        this.setState({ value: null }) // for onBlur()
        this.inputRef.current.blur() // calls onBlur()
        return
    }
  }

  onBlur = () => {
    // If 'Escape' was handled, `value` will be null _within setState()_.
    this.setState(({ value }) => {
      if (value === null) {
        this.props.onCancel()
      } else {
        this.props.onSubmit(this.state.value)
      }
    })
  }

  render () {
    const value = this.state.value === null ? this.props.value : this.state.value

    return (
      <div className='editable-tab-name'>
        <span className='size-calculator'>{value}</span>
        <input
          name='tab-name'
          ref={this.inputRef}
          value={value}
          onChange={this.onChange}
          onKeyDown={this.onKeyDown}
          onBlur={this.onBlur}
        />
      </div>
    )
  }
}
