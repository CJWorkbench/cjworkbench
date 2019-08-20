// Drop-down menu on Workflows List page to sort the list

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem, DropdownDivider } from '../components/Dropdown'

export default class SortMenu extends React.Component {
  static propTypes = {
    comparator: PropTypes.oneOf(['last_update|ascending', 'last_update|descending', 'name|ascending', 'name|descending']).isRequired,
    setComparator: PropTypes.func.isRequired // func(comparator) => undefined
  }

  handleClickComparator = (ev) => {
    const comparator = ev.target.getAttribute('data-comparator')
    this.props.setComparator(comparator)
  }

  get icon () {
    return this.props.sortDirection === 'ascending' ? 'icon-caret-up' : 'icon-caret-down'
  }

  render () {
    return (
      <div className='sort-menu'>
        <UncontrolledDropdown>
          <DropdownToggle>
            Sort <i className={this.icon} />
          </DropdownToggle>
          <DropdownMenu>
            <DropdownItem data-comparator='last_update|descending' onClick={this.handleClickComparator}>Last modified</DropdownItem>
            <DropdownItem data-comparator='last_update|ascending' onClick={this.handleClickComparator}>Oldest modified</DropdownItem>
            <DropdownDivider />
            <DropdownItem data-comparator='name|ascending' onClick={this.handleClickComparator}>Alphabetical</DropdownItem>
            <DropdownItem data-comparator='name|descending' onClick={this.handleClickComparator}>Reverse alphabetical</DropdownItem>
          </DropdownMenu>
        </UncontrolledDropdown>
      </div>
    )
  }
}
