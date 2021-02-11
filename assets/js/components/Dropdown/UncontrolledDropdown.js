import { useReducer } from 'react'
import PropTypes from 'prop-types'
import Dropdown from './Dropdown'

export default function UncontrolledDropdown (props) {
  const [isOpen, toggleOpen] = useReducer(open => !open, false)
  const { disabled, children } = props

  return (
    <Dropdown
      isOpen={isOpen}
      toggle={toggleOpen}
      disabled={disabled}
    >
      {children}
    </Dropdown>
  )
}
UncontrolledDropdown.propTypes = {
  disabled: PropTypes.bool,
  children: PropTypes.node.isRequired
}
