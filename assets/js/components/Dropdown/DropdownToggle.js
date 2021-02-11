import { useContext } from 'react'
import PropTypes from 'prop-types'
import { DropdownContext } from './Dropdown'

export default function DropdownToggle (props) {
  const {
    isOpen,
    disabled,
    setToggleElement,
    toggle
  } = useContext(DropdownContext)

  const {
    className = 'btn btn-secondary',
    children,
    caret,
    title,
    name
  } = props
  const classNames = [className]
  if (caret) classNames.push('dropdown-toggle')

  return (
    <button
      className={classNames.join(' ')}
      name={name}
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
  className: PropTypes.string, // default 'btn btn-secondary'
  caret: PropTypes.bool, // adds 'dropdown-toggle' className
  name: PropTypes.string, // HTML `name` property (useful in tests, CSS)
  title: PropTypes.string
}
