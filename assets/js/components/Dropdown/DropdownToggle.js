import React from 'react'
import PropTypes from 'prop-types'
import { Reference as PopperReference } from 'react-popper'
import { DropdownContext } from './Dropdown'

export default class DropdownToggle extends React.PureComponent {
  static propTypes = {
    children: PropTypes.node.isRequired,
    caret: PropTypes.bool, // adds 'dropdown-toggle' className
    className: PropTypes.string, // adds to `btn btn-secondary (dropdown-toggle?)`
    title: PropTypes.string
  }
  static contextType = DropdownContext

  render () {
    const { children, caret, title, className } = this.props
    const { isOpen, disabled, toggle } = this.context
    const classNames = [ 'btn btn-secondary' ]
    if (caret) classNames.push('dropdown-toggle')
    if (className) classNames.push(className)

    return (
      <PopperReference>
        {({ ref }) => (
          <button
            className={classNames.join(' ')}
            onClick={toggle}
            disabled={disabled}
            aria-expanded={isOpen}
            children={children}
            title={title}
            ref={ref}
          />
        )}
      </PopperReference>
    )
  }
}
