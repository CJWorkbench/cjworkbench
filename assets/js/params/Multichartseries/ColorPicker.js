import React from 'react'
import PropTypes from 'prop-types'
import Button from 'reactstrap/lib/Button'
import InputGroup from 'reactstrap/lib/InputGroup'
import InputGroupAddon from 'reactstrap/lib/InputGroupAddon'
import Input from 'reactstrap/lib/Input'
import Popover from 'reactstrap/lib/Popover'
import PopoverBody from 'reactstrap/lib/PopoverBody'

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

    return (
      <InputGroup className={this.isValid ? 'valid' : 'invalid'}>
        <InputGroupAddon addonType='prepend'>
          <Button name='choose-custom-color' className='choose-custom-color' onClick={this.onClickButton} style={{ background: this.effectiveColor }}></Button>
        </InputGroupAddon>
        <Input
          placeholder='#000000'
          value={value}
          onChange={this.onChange}
          onKeyDown={this.onKeyDown}
        />
      </InputGroup>
    )
  }
}


/**
 * A simulation for `<input type="color" list=...`, which has lousy
 * cross-browser support in 2018.
 */
export default class ColorPicker extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    value: PropTypes.string, // Like '#abcdef'; default is '#000000'
    choices: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
    onChange: PropTypes.func.isRequired, // onChange('#abcdef') => undefined
  }

  state = {
    isOpen: false
  }

  buttonRef = React.createRef()

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
    const { name, value, choices } = this.props
    const { isOpen } = this.state
    const safeValue = value || '#000000'

    return (
      <React.Fragment>
        <button type='button' ref={this.buttonRef} title='Pick color' onClick={this.toggleOpen} className='btn color-picker' style={{ background: safeValue }}>
          <i className='color-picker' />
        </button>
        { isOpen ? (
          <Popover placement='bottom' innerClassName='color-picker-popover' isOpen={isOpen} target={this.buttonRef} toggle={this.close}>
            <PopoverBody>
              {choices.map(color => (
                <ColorChoice key={'choice-' + color} color={color} onClick={this.onChange} />
              ))}
              <CustomColorChoice
                key={'custom-choice-' + safeValue}
                defaultValue={safeValue}
                onChange={this.onChange}
                onClose={this.close}
              />
            </PopoverBody>
          </Popover>
        ) : null }
      </React.Fragment>
    )
  }
}
