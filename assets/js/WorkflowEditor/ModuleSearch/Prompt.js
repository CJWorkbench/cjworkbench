import React from 'react'
import PropTypes from 'prop-types'

export default class Prompt extends React.PureComponent {
  static propTypes = {
    value: PropTypes.string.isRequired, // may be empty
    cancel: PropTypes.func.isRequired, // func() => undefined -- should close this prompt
    onChange: PropTypes.func.isRequired // func(value) => undefined
  }

  inputRef = React.createRef()

  componentDidMount () {
    // auto-focus
    this.inputRef.current.focus()
  }

  onChange = (ev) => {
    this.props.onChange(ev.target.value)
  }

  onKeyDown = (ev) => {
    if (ev.keyCode === 27) this.props.cancel() // Esc => cancel
  }

  onSubmit = (ev) => {
    ev.preventDefault()
  }

  render () {
    const { value, cancel } = this.props

    return (
      <form className='module-search-field' onSubmit={this.onSubmit} onReset={cancel}>
        <input
          type='search'
          name='moduleQ'
          placeholder='Search…'
          autoComplete='off'
          ref={this.inputRef}
          value={value}
          onChange={this.onChange}
          onKeyDown={this.onKeyDown}
        />
        <button type='reset' className='reset' title='Close Search'><i className='icon-close' /></button>
      </form>
    )
  }
}
