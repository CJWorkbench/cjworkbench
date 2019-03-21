import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import { Manager as PopperManager, Target as PopperTarget, Popper, Arrow } from 'react-popper'

class ColorChoice extends React.PureComponent {
  static propTypes = {
    color: PropTypes.string.isRequired, // like '#abcdef'
    onClick: PropTypes.func.isRequired, // onClick('#abcdef') => undefined
  }

  onClick = () => {
    this.props.onClick(this.props.color)
  }

  render () {
    const { color } = this.props
    const name = 'color-' + color.slice(1)

    return (
      <button
        type='button'
        name={name}
        onClick={this.onClick}
        className='color-choice'
        style={{ backgroundColor: color}}
      ></button>
    )
  }
}


/**
 * a <button> and <input> that let the user write a color.
 */
class CustomColorChoice extends React.PureComponent {
  static propTypes = {
    defaultValue: PropTypes.string.isRequired, // '#abcdef'-style string
    onChange: PropTypes.func.isRequired, // onChange('#abcdef') => undefined
    onClose: PropTypes.func.isRequired, // onClose() => undefined -- if Escape is pressed
  }

  state = {
    value: this.props.defaultValue,
  }

  get effectiveColor () {
    if (!this.isValid) return '#000000'

    const { value } = this.state
    return value[0] === '#' ? value : `#${value}`
  }

  get isValid () {
    return /^#?[0-9a-fA-F]{6}$/.test(this.state.value)
  }

  onClickButton = () => {
    this.props.onChange(this.effectiveColor)
  }

  onChange = (ev) => {
    this.setState({ value: ev.target.value })
  }

  onKeyDown = (ev) => {
    switch (ev.key) {
      case 'Enter':
        const el = ev.target
        if (this.isValid) {
          this.props.onChange(this.effectiveColor)
          return this.props.onClose()
        }
        break
      case 'Escape':
        this.props.onClose()
        break
    }
  }

  render () {
    const { value } = this.state
    const safeValue = value || '#000000'

    return (
      <div className={`input-group ${this.isValid ? 'valid' : 'invalid'}`}>
        <div className='input-group-prepend'>
          <button
            type='button'
            name='choose-custom-color'
            className='btn choose-custom-color'
            onClick={this.onClickButton}
            style={{ background: this.effectiveColor }}
          />
        </div>
        <input
          className='form-control'
          placeholder='#000000'
          value={value}
          onChange={this.onChange}
          onKeyDown={this.onKeyDown}
        />
      </div>
    )
  }
}
            

class ColorPickerPopover extends React.PureComponent {
  static propTypes = {
    value: PropTypes.string, // Like '#abcdef'; default is '#000000'
    choices: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
    onChange: PropTypes.func.isRequired, // onChange('#abcdef') => undefined
    onClose: PropTypes.func.isRequired // onClose() => undefined
  }

  ref = React.createRef()

  componentDidMount () {
    document.addEventListener('mousedown', this.onMouseDown, true)
  }

  componentWillUnmount () {
    document.removeEventListener('mousedown', this.onMouseDown, true)
  }

  /**
   * Close the popover if we click outside it.
   */
  onMouseDown = (ev) => {
    if (this.ref.current && !this.ref.current.contains(ev.target)) {
      this.props.onClose()
    }
  }

  render () {
    const { safeValue, choices, onChange, onClose } = this.props

    return (
      <Popper placement='bottom'>
        {({ popperProps }) => ReactDOM.createPortal((
          <div className={`popover show bs-popover-${popperProps['data-placement']} color-picker-popover`} {...popperProps}>
            <Arrow className='arrow' />
            <div ref={this.ref} className='popover-body'>
              {choices.map(color => (
                <ColorChoice key={'choice-' + color} color={color} onClick={onChange} />
              ))}
              <CustomColorChoice
                key={'custom-choice-' + safeValue}
                defaultValue={safeValue}
                onChange={onChange}
                onClose={onClose}
              />
            </div>
          </div>
        ), document.body)}
      </Popper>
    )
  }
}


/**
 * A simulation for `<input type="color" list=...`, which has lousy
 * cross-browser support in 2018.
 */
export default class ColorPicker extends React.PureComponent {
  static propTypes = {
    value: PropTypes.string.isRequired, // Like '#abcdef'
    choices: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
    onChange: PropTypes.func.isRequired, // onChange('#abcdef') => undefined
  }

  state = {
    isOpen: false
  }

  toggleOpen = () => {
    this.setState({ isOpen: !this.state.isOpen })
  }

  close = () => {
    this.setState({ isOpen: false })
  }

  onChange = (color) => {
    this.props.onChange(color)
    this.setState({ isOpen: false })
  }

  render () {
    const { value, choices } = this.props
    const { isOpen } = this.state
    const safeValue = value || '#000000'

    return (
      <PopperManager>
        <PopperTarget>
          {({ targetProps }) => (
            <button type='button' title='Pick color' onClick={this.toggleOpen} className='btn color-picker' style={{ background: safeValue }} {...targetProps}>
              <i className='color-picker' />
            </button>
          )}
        </PopperTarget>
        {isOpen ? (
          <ColorPickerPopover
            safeValue={safeValue}
            choices={choices}
            onChange={this.onChange}
            onClose={this.close}
          />
        ) : null}
      </PopperManager>
    )
  }
}
