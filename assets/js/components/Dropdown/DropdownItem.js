import React from 'react'
import PropTypes from 'prop-types'
import { DropdownContext } from './Dropdown'

/**
 * Menu item (link or button), Workbench-styled.
 *
 * Usage:
 *
 * <Dropdown>
 *   <DropdownToggle>Open</DropdownToggle>
 *   <DropdownMenu>
 *    <DropdownItem icon="icon-close" onClick={this.close}>Close</DropdownItem>
 *    <DropdownItem icon="icon-bin" onClick={this.delete}>Delete</DropdownItem>
 *   </DropdownMenu>
 * </Dropdown>
 *
 * https://getbootstrap.com/docs/4.0/components/dropdowns/#menu-items
 */
export default class DropdownItem extends React.PureComponent {
  static propTypes = {
    children: PropTypes.node.isRequired,
    className: PropTypes.string, // will be added to 'dropdown-item'
    icon: PropTypes.string, // 'icon-close' or empty
    href: PropTypes.string, // for <a> (otherwise, see onClick)
    onClick: PropTypes.func, // for <button> (otherwise, see href)
    active: PropTypes.bool, // adds CSS class
    disabled: PropTypes.bool // if set, cannot be clicked
    // Other props -- e.g., 'data-comparator' -- will be assed through as-is to <button>/<a>.
  }

  static contextType = DropdownContext

  onClick = this.props.onClick ? (
    (ev) => {
      this.props.onClick(ev)
      this.context.toggle()
    }
  ) : undefined

  render () {
    const { children, href, className, icon, active, disabled, ...rest } = this.props
    const Tag = href ? 'a' : 'button'

    const classNames = [ 'dropdown-item' ]
    if (className) classNames.push(className)
    if (active) classNames.push('active')

    return (
      <Tag
        {...rest /* pass through all other options -- _first_, so e.g. we'll overwrite onClick+className */}
        className={classNames.join(' ')}
        href={href}
        onClick={this.onClick}
        tabIndex={0}
        role='menuitem'
        disabled={disabled}
      >
        {icon ? <i className={icon} /> : null}
        {children}
      </Tag>
    )
  }
}
