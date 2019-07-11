import React from 'react'
import PropTypes from 'prop-types'
import { Manager as PopperManager } from 'react-popper'

export const DropdownContext = React.createContext()
DropdownContext.Provider.propTypes = {
  value: PropTypes.shape({
    disabled: PropTypes.bool.isRequired,
    isOpen: PropTypes.bool.isRequired,
    toggle: PropTypes.func.isRequired,
    toggleRef: PropTypes.shape({ current: PropTypes.instanceOf(Element) }).isRequired
  }).isRequired
}

/**
 * Bootstrap dropdown menu
 *
 * Reference: https://getbootstrap.com/docs/4.0/components/dropdowns/#overview
 */
export default class Dropdown extends React.PureComponent {
  static propTypes = {
    isOpen: PropTypes.bool.isRequired,
    toggle: PropTypes.func.isRequired,
    disabled: PropTypes.bool,
    children: PropTypes.node.isRequired
  }

  toggleRef = React.createRef()

  toggle = (ev) => {
    const { disabled, toggle } = this.props
    if (disabled) return
    toggle(ev)
  }

  render () {
    const { disabled, isOpen, children } = this.props

    const dropdownContext = {
      disabled: !!disabled,
      isOpen,
      toggle: this.toggle,
      toggleRef: this.toggleRef
    }

    return (
      <PopperManager tag={false}>
        <DropdownContext.Provider value={dropdownContext}>
          <div className='dropdown' children={children} />
        </DropdownContext.Provider>
      </PopperManager>
    )
  }
}
