// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownMenu, DropdownToggle, DropdownItem, DropdownDivider } from '../components/Dropdown'

export default class ColumnContextMenu extends React.Component {
  static propTypes = {
    onClickAction: PropTypes.func.isRequired, // func(idName, forceNewModule, params)
    columnType: PropTypes.string.isRequired,
    renameColumn: PropTypes.func.isRequired
  }

  createOrUpdate (idName, extraParams={}) {
    this.props.onClickAction(idName, false, extraParams)
  }

  create (idName, extraParams={}) {
    this.props.onClickAction(idName, true, extraParams)
  }

  renameColumn = (...args) => {
    this.props.renameColumn(...args)
  }

  duplicateColumn = () => this.createOrUpdate('duplicatecolumns')
  sortAscending = () => this.createOrUpdate('sort', { is_ascending: true })
  sortDescending = () => this.createOrUpdate('sort', { is_ascending: false })
  addNewFilter = () => this.create('filter')
  extractNumbers = () => this.createOrUpdate('converttexttonumber')
  cleanText = () => this.createOrUpdate('clean-text')
  dropColumn = () => this.createOrUpdate('selectcolumns', { drop_or_keep: 0 })
  convertDate = () => this.createOrUpdate('convert-date')
  convertText = () => this.createOrUpdate('converttotext')

  render() {
    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='icon-caret-down' />
        </DropdownToggle>
        <DropdownMenu>
          <DropdownItem onClick={this.renameColumn} className='rename-column-header' icon='icon-edit'>Rename</DropdownItem>
          <DropdownItem onClick={this.duplicateColumn} className='duplicatecolumns' icon='icon-duplicate'>Duplicate</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.sortAscending} className='sort-ascending' icon='icon-sort-up'>Sort ascending</DropdownItem>
          <DropdownItem onClick={this.sortDescending} className='sort-descending' icon='icon-sort-down'>Sort descending</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.addNewFilter} className='filter-column' icon='icon-filter'>Filter</DropdownItem>
          <DropdownItem onClick={this.cleanText} className='clean-text' icon='icon-clean'>Clean Text</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.convertDate} className='convert-date' icon='icon-calendar'>Convert to date & time</DropdownItem>
          <DropdownItem onClick={this.extractNumbers} className='converttexttonumber' icon='icon-number'>Convert to numbers</DropdownItem>
          <DropdownItem onClick={this.convertText} className='converttotext' icon='icon-text'>Convert to text</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.dropColumn} className='drop-column' icon='icon-removec'>Delete column</DropdownItem>
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}
