/* globals HTMLElement */
import { createContext, useCallback, useState, useMemo } from 'react'
import PropTypes from 'prop-types'
import { usePopper } from 'react-popper'

export const DropdownContext = createContext()
DropdownContext.Provider.propTypes = {
  value: PropTypes.shape({
    disabled: PropTypes.bool.isRequired,
    isOpen: PropTypes.bool.isRequired,
    toggle: PropTypes.func.isRequired,
    setToggleElement: PropTypes.func.isRequired,
    toggleElement: PropTypes.instanceOf(HTMLElement), // or null
    setMenuElement: PropTypes.func.isRequired,
    menuElement: PropTypes.instanceOf(HTMLElement), // or null
    popperStuff: PropTypes.object.isRequired
  }).isRequired
}

const PopperOptions = {
  placement: 'bottom-end',
  modifiers: [{ name: 'preventOverflow', options: { boundary: 'viewport' } }]
}

/**
 * Bootstrap dropdown menu
 *
 * Reference: https://getbootstrap.com/docs/4.0/components/dropdowns/#overview
 */
export default function Dropdown (props) {
  const { isOpen, toggle, disabled = false, children } = props

  const handleClickToggle = useCallback(
    ev => {
      if (disabled) return
      toggle(ev)
    },
    [disabled, toggle]
  )
  const [toggleElement, setToggleElement] = useState(null)
  const [menuElement, setMenuElement] = useState(null)
  const popperStuff = usePopper(toggleElement, menuElement, PopperOptions)

  const dropdownContext = useMemo(
    () => ({
      disabled,
      isOpen,
      toggle: handleClickToggle,
      setToggleElement,
      toggleElement,
      setMenuElement,
      menuElement,
      popperStuff
    }),
    [
      disabled,
      isOpen,
      handleClickToggle,
      setToggleElement,
      toggleElement,
      setMenuElement,
      menuElement,
      popperStuff
    ]
  )

  return (
    <DropdownContext.Provider value={dropdownContext}>
      <div className='dropdown'>{children}</div>
    </DropdownContext.Provider>
  )
}
Dropdown.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  toggle: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  children: PropTypes.node.isRequired
}
