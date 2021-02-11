import { useContext, useCallback, useEffect } from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import { DropdownContext } from './Dropdown'

const KeyCodes = {
  Tab: 9
}

/**
 * Dropdown menu that is actually shown.
 *
 * This is not to be confused with <DropdownMenu>, which sometimes renders as
 * null.
 */
export function OpenDropdownMenu (props) {
  const { children } = props
  const { setMenuElement, menuElement, toggleElement, popperStuff, toggle } = useContext(DropdownContext)

  const handleClickDocument = useCallback(ev => {
    if (!menuElement) {
      // we're in the process of mounting -- the click handler was added mid-click
      // while the user clicked the DropdownToggle component. Ignore this event.
      return
    }

    // Copy/paste from Reactstrap src/Dropdown.js
    if (ev && (ev.which === 3 || (ev.type === 'keyup' && ev.which !== KeyCodes.Tab))) return

    if (menuElement.contains(ev.target) && menuElement !== ev.target && (ev.type !== 'keyup' || ev.which === KeyCodes.Tab)) {
      return
    }

    toggle(ev)
    ev.stopPropagation() // prevent event from triggering the toggle button in the same click -- which would reopen the menu
  }, [menuElement, toggle])
  useEffect(() => {
    const Events = ['click', 'touchstart', 'keyup']
    Events.forEach(eventName => {
      document.addEventListener(eventName, handleClickDocument, true)
    })
    return () => {
      Events.forEach(eventName => {
        document.removeEventListener(eventName, handleClickDocument, true)
      })
    }
  }, [handleClickDocument])

  /**
   * Handle keyboard navigation (only when menu is open)
   *
   * Up/Down, Ctrl+n/Ctrl+p: focus() next/previous menu item (wrapping).
   * Any letter: focus() first menu item that starts with that letter.
   * Space/Enter: do nothing -- if they happen on a focused menu item, that'll
   *              trigger the menu item's onClick() instead.
   * Escape/Tab: close menu and focus trigger element.
   */
  const handleKeyDown = useCallback(ev => {
    /**
     * Focus next (by=1) or previous (by=-1) menuitem.
     */
    const moveFocus = (by) => {
      if (!menuElement) return

      const menuItems = [...menuElement.querySelectorAll('[role=menuitem]')]
      if (!menuItems.length) return

      const currentIndex = menuItems.indexOf(document.activeElement) // maybe -1
      let nextIndex = currentIndex + by
      if (nextIndex < 0) nextIndex = menuItems.length - 1 // wrap backwards
      if (nextIndex >= menuItems.length) nextIndex = 0
      menuItems[nextIndex].focus()
    }

    const keystroke = (ev.ctrlKey ? 'Ctrl+' : '') + ev.key // 'Ctrl+n', 'ArrowUp', 'Tab', ...
    switch (keystroke) {
      case 'Escape':
      case 'Tab': {
        toggle(ev)
        if (toggleElement) toggleElement.focus()
        ev.preventDefault()
        return
      }

      case 'ArrowUp':
      case 'Ctrl+p':
        moveFocus(-1)
        ev.preventDefault()
        return

      case 'ArrowDown':
      case 'Ctrl+n':
        moveFocus(1)
        ev.preventDefault() // Ctrl+n shoudn't open new browser window
    }
  }, [toggle, menuElement, toggleElement])
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown, true)
    return () => document.removeEventListener('keydown', handleKeyDown, true)
  }, [handleKeyDown])

  return ReactDOM.createPortal((
    <div
      className='dropdown-menu-portal'
      ref={setMenuElement}
      style={popperStuff.styles.popper}
      {...(popperStuff.attributes.popper || {})}
    >
      <div className='dropdown-menu' role='menu' children={children} />
    </div>
  ), document.body)
}
OpenDropdownMenu.propTypes = {
  children: PropTypes.node.isRequired
}

/**
 * OpenDropdownMenu, or null -- depending on whether the Dropdown is open.
 *
 * This delegates to <OpenDropdownMenu> when the dropdown is open.
 * OpenDropdownMenu will be mounted or unmounted, and it'll manage event
 * handlers during mount/unmount.
 */
export default function DropdownMenu (props) {
  const { isOpen, disabled } = useContext(DropdownContext)
  if (disabled || !isOpen) {
    return null
  } else {
    return <OpenDropdownMenu {...props} />
  }
}
DropdownMenu.propTypes = {
  children: PropTypes.node.isRequired
}
