import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import { Popper } from 'react-popper'
import { DropdownContext } from './Dropdown'

const KeyCodes = {
  Tab: 9
}

const PopperModifiers = {
  preventOverflow: {
    boundariesElement: 'viewport'
  }
}

/**
 * Dropdown menu that is actually shown.
 *
 * This is not to be confused with <DropdownMenu>, which sometimes renders as
 * null.
 */
class OpenDropdownMenu extends React.PureComponent {
  static propTypes = {
    children: PropTypes.node.isRequired
  }
  static contextType = DropdownContext

  ref = React.createRef()

  componentDidMount () {
    ['click', 'touchstart', 'keyup'].forEach(eventName =>
      document.addEventListener(eventName, this.onClickDocument, true)
    )
    document.addEventListener('keydown', this.onKeyDown, true)
  }

  componentWillUnmount () {
    ['click', 'touchstart', 'keyup'].forEach(eventName =>
      document.removeEventListener(eventName, this.onClickDocument, true)
    )
    document.removeEventListener('keydown', this.onKeyDown, true)
  }

  onClickDocument = (ev) => {
    const container = this.ref.current
    if (!this.ref.current) {
      // we're in the process of mounting -- the click handler was added mid-click
      // while the user clicked the DropdownToggle component. Ignore this event.
      return
    }

    // Copy/paste from Reactstrap src/Dropdown.js
    if (ev && (ev.which === 3 || (ev.type === 'keyup' && ev.which !== KeyCodes.Tab))) return

    if (container.contains(ev.target) && container !== ev.target && (ev.type !== 'keyup' || ev.which === KeyCodes.Tab)) {
      return
    }

    this.context.toggle(ev)
    ev.stopPropagation() // prevent event from triggering the toggle button in the same click -- which would reopen the menu
  }

  /**
   * Focus next (by=1) or previous (by=-1) menuitem.
   */
  moveFocus (by) {
    const container = this.ref.current
    if (!container) return

    const menuItems = [ ...container.querySelectorAll('[role=menuitem]') ]
    console.log(menuItems)
    if (!menuItems.length) return

    const currentIndex = menuItems.indexOf(document.activeElement) // maybe -1
    let nextIndex = currentIndex + by
    if (nextIndex < 0) nextIndex = menuItems.length - 1 // wrap backwards
    if (nextIndex >= menuItems.length) nextIndex = 0
    menuItems[nextIndex].focus()
  }

  /**
   * Handle keyboard navigation (only when menu is open)
   *
   * Up/Down, Ctrl+n/Ctrl+p: focus() next/previous menu item (wrapping).
   * Any letter: focus() first menu item that starts with that letter.
   * Space/Enter: do nothing -- if they happen on a focused menu item, that'll
   *              trigger the menu item's onClick() instead.
   * Escape/Tab: close menu and focus trigger element.
   */
  onKeyDown = (ev) => {
    const keystroke = (ev.ctrlKey ? 'Ctrl+' : '') + ev.key // 'Ctrl+n', 'ArrowUp', 'Tab', ...
    switch (keystroke) {
      case 'Escape':
      case 'Tab':
        const { toggle, toggleRef } = this.context
        toggle(ev)
        if (toggleRef.current) toggleRef.current.focus()
        ev.preventDefault()
        return

      case 'ArrowUp':
      case 'Ctrl+p':
        this.moveFocus(-1)
        ev.preventDefault()
        return

      case 'ArrowDown':
      case 'Ctrl+n':
        this.moveFocus(1)
        ev.preventDefault() // Ctrl+n shoudn't open new browser window
    }
  }

  render () {
    const { children } = this.props

    return ReactDOM.createPortal((
      <Popper modifiers={PopperModifiers} placement='bottom-end'>
        {({ ref, style, placement }) => (
          <div
            className='dropdown-menu-portal'
            ref={ref}
            style={style}
            data-placement={placement}
          >
            <div ref={this.ref} className='dropdown-menu' role='menu' children={children} />
          </div>
        )}
      </Popper>
    ), document.body)
  }
}

/**
 * OpenDropdownMenu, or null -- depending on whether the Dropdown is open.
 *
 * This delegates to <OpenDropdownMenu> when the dropdown is open.
 * OpenDropdownMenu will be mounted or unmounted, and it'll manage event
 * handlers during mount/unmount.
 */
export default class DropdownMenu extends React.PureComponent {
  static propTypes = {
    children: PropTypes.node.isRequired
  }
  static contextType = DropdownContext

  render () {
    const { disabled, isOpen } = this.context
    if (disabled || !isOpen) {
      return null
    } else {
      return <OpenDropdownMenu {...this.props} />
    }
  }
}
