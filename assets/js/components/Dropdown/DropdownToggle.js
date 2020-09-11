import React from 'react'
import PropTypes from 'prop-types'
import { DropdownContext } from './Dropdown'

export default function DropdownToggle (props) {
  const { isOpen, disabled, setToggleElement, toggle } = React.useContext(DropdownContext)

  const { children, caret, title, className } = props
  const classNames = ['btn btn-secondary']
  if (caret) classNames.push('dropdown-toggle')
  if (className) classNames.push(className)

  return (
    <button
      className={classNames.join(' ')}
      onClick={toggle}
      disabled={disabled}
      aria-expanded={isOpen}
      children={children}
      title={title}
      ref={setToggleElement}
    />
  )
}
DropdownToggle.propTypes = {
  children: PropTypes.node.isRequired,
  caret: PropTypes.bool, // adds 'dropdown-toggle' className
  className: PropTypes.string, // adds to `btn btn-secondary (dropdown-toggle?)`
  title: PropTypes.string
}
