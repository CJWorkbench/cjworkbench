// Drop-down menu on Workflows List page to sort the list

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem, DropdownDivider } from '../components/Dropdown'
import { I18n } from '@lingui/react'
import { Trans,t } from '@lingui/macro'

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
            <DropdownItem data-comparator='last_update|descending' onClick={this.handleClickComparator}><Trans id="workflow.lastmodified">Last modified</Trans></DropdownItem>
            <DropdownItem data-comparator='last_update|ascending' onClick={this.handleClickComparator}><Trans id="workflow.oldestmodified">Oldest modified</Trans></DropdownItem>
            <DropdownDivider />
            <DropdownItem data-comparator='name|ascending' onClick={this.handleClickComparator}><Trans id="workflow.alphabetical">Alphabetical</Trans></DropdownItem>
            <DropdownItem data-comparator='name|descending' onClick={this.handleClickComparator}><Trans id="workflow.reversealphabet">Reverse alphabetical</Trans></DropdownItem>
          </DropdownMenu>
        </UncontrolledDropdown>
      </div>
    )
  }
}
