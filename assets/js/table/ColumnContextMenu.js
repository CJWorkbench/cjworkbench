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

  createOrUpdate (idName, extraParams = {}) {
    this.props.onClickAction(idName, false, extraParams)
  }

  create (idName, extraParams = {}) {
    this.props.onClickAction(idName, true, extraParams)
  }

  handleRenameColumn = (...args) => { this.props.renameColumn(...args) }
  handleDuplicateColumn = () => this.createOrUpdate('duplicatecolumns')
  handleSortAscending = () => this.createOrUpdate('sort', { is_ascending: true })
  handleSortDescending = () => this.createOrUpdate('sort', { is_ascending: false })
  handleAddNewFilter = () => this.create('filter')
  handleExtractNumbers = () => this.createOrUpdate('converttexttonumber')
  handleCleanText = () => this.createOrUpdate('clean-text')
  handleDropColumn = () => this.createOrUpdate('selectcolumns', { keep: false })
  handleConvertDate = () => this.createOrUpdate('convert-date')
  handleConvertText = () => this.createOrUpdate('converttotext')
  handleFormatNumbers = () => this.create('formatnumbers', { format: '{:,}' })

  render () {
    const { columnType } = this.props

    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='icon-caret-down' />
        </DropdownToggle>
        <DropdownMenu>
          <DropdownItem onClick={this.handleRenameColumn} className='rename-column-header' icon='icon-edit'>Rename</DropdownItem>
          <DropdownItem onClick={this.handleDuplicateColumn} className='duplicatecolumns' icon='icon-duplicate'>Duplicate</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleSortAscending} className='sort-ascending' icon='icon-sort-up'>Sort ascending</DropdownItem>
          <DropdownItem onClick={this.handleSortDescending} className='sort-descending' icon='icon-sort-down'>Sort descending</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleAddNewFilter} className='filter-column' icon='icon-filter'>Filter</DropdownItem>
          <DropdownItem onClick={this.handleCleanText} className='clean-text' icon='icon-clean'>Clean Text</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleConvertDate} className='convert-date' icon='icon-calendar'>Convert to date & time</DropdownItem>
          <DropdownItem onClick={this.handleExtractNumbers} className='converttexttonumber' icon='icon-number'>Convert to numbers</DropdownItem>
          <DropdownItem onClick={this.handleConvertText} className='converttotext' icon='icon-text'>Convert to text</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleFormatNumbers} className='formatnumbers' icon='icon-number' disabled={columnType !== 'number'}>Format numbers</DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleDropColumn} className='drop-column' icon='icon-removec'>Delete column</DropdownItem>
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}
