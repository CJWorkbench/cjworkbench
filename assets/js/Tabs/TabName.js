import React from 'react'
import PropTypes from 'prop-types'

export default class TabName extends React.PureComponent {
  static propTypes = {
    inputRef: PropTypes.shape({ current: PropTypes.instanceOf(Element) }).isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    isSelected: PropTypes.bool.isRequired,
    value: PropTypes.string.isRequired,
    onSubmit: PropTypes.func.isRequired, // func(value) => undefined
  }

  state = {
    value: null
  }

  onChange = (ev) => {
    this.setState({ value: ev.target.value })
  }

  onKeyDown = (ev) => {
    switch (ev.key) {
      case 'Enter':
        this.props.onSubmit(this.state.value)
        this.setState({ value: null }) // for onBlur()
        this.props.inputRef.current.blur()
        return
      case 'Escape':
        this.setState({ value: null }) // for onBlur()
        this.props.inputRef.current.blur()
        return
    }
  }

  onBlur = () => {
    // onKeyDown may have set value=null. If it did, we'll only detect that
    // within the setState() _callback_.
    this.setState(({ value }) => {
      if (value === null) {
        // onKeyDown already handled this (or there was no edit)
      } else {
        this.props.onSubmit(this.state.value)
      }
    })
  }

  render () {
    const { isReadOnly, isSelected, inputRef } = this.props
    const value = this.state.value === null ? this.props.value : this.state.value

    /*
     * Two equivalent representations of the same value:
     *
     * <span>: the text, not editable, used to size text
     * <input>: what the user sees
     */
    return (
      <div
        className='tab-name'
      >
        <span className='size-calculator'>{value}</span>
        <input
          name='tab-name'
          placeholder='…'
          ref={inputRef}
          value={value}
          disabled={isReadOnly || !isSelected}
          onChange={this.onChange}
          onKeyDown={this.onKeyDown}
          onBlur={this.onBlur}
        />
      </div>
    )
  }
}
