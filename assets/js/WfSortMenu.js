// Drop-down menu on Workflows List page to sort the list

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from './components/Dropdown'

export default class WfSortMenu extends React.Component {
  constructor(props) {
    super(props)
  }
  sortNameAsc = () => this.props.setSortType({type: 'name', direction: 'ascending'})
  sortNameDesc = () => this.props.setSortType({type: 'name', direction: 'descending'})
  sortDateAsc = () => this.props.setSortType({type: 'last_update', direction: 'ascending'})
  sortDateDesc = () => this.props.setSortType({type: 'last_update', direction: 'descending'})
  setSortIcon = () => {
    if (this.props.sortDirection === 'ascending') return 'icon-caret-up'
    else return 'icon-caret-down'
  }

  render () {
    return (
      <UncontrolledDropdown>
        <DropdownToggle className='btn btn-secondary context-button'>
          <i className={this.setSortIcon()}></i>
        </DropdownToggle>
        <DropdownMenu positionFixed right>
          <DropdownItem onClick={this.sortDateAsc} className='test-sort-date-ascending'>
            <span>Last modified</span>
          </DropdownItem>
          <DropdownItem onClick={this.sortDateDesc} className='test-sort-date-descending'>
            <span>Oldest modified</span>
          </DropdownItem>
          <DropdownItem divider />
          <DropdownItem onClick={this.sortNameAsc} className='test-sort-name-ascending'>
            <span>Alphabetical</span>
          </DropdownItem>
          <DropdownItem onClick={this.sortNameDesc} className='test-sort-name-descending'>
            <span>Reverse alphabetical</span>
          </DropdownItem>
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}

WfSortMenu.propTypes = {
  setSortType: PropTypes.func.isRequired,
  sortDirection: PropTypes.string.isRequired
}
