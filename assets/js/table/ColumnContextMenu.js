// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownMenu, DropdownToggle, DropdownItem, DropdownDivider } from '../components/Dropdown'
import { Trans } from '@lingui/macro'

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
          <DropdownItem onClick={this.handleRenameColumn} className='rename-column-header' icon='icon-edit'><Trans id='js.table.ColumnContextMenu.rename.'>Rename</Trans></DropdownItem>
          <DropdownItem onClick={this.handleDuplicateColumn} className='duplicatecolumns' icon='icon-duplicate'><Trans id='js.table.ColumnContextMenu.duplicate'>Duplicate</Trans></DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleSortAscending} className='sort-ascending' icon='icon-sort-up'><Trans id='js.table.ColumnContextMenu.sortAscending'>Sort ascending</Trans></DropdownItem>
          <DropdownItem onClick={this.handleSortDescending} className='sort-descending' icon='icon-sort-down'><Trans id='js.table.ColumnContextMenu.sortDescending'>Sort descending</Trans></DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleAddNewFilter} className='filter-column' icon='icon-filter'><Trans id='js.table.ColumnContextMenu.filter'>Filter</Trans></DropdownItem>
          <DropdownItem onClick={this.handleCleanText} className='clean-text' icon='icon-clean'><Trans id='js.table.ColumnContextMenu.cleanText'>Clean Text</Trans></DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleConvertDate} className='convert-date' icon='icon-calendar'><Trans id='js.table.ColumnContextMenu.convertToDateTime'>Convert to date & time</Trans></DropdownItem>
          <DropdownItem onClick={this.handleExtractNumbers} className='converttexttonumber' icon='icon-number'><Trans id='js.table.ColumnContextMenu.convertToNumbers'>Convert to numbers</Trans></DropdownItem>
          <DropdownItem onClick={this.handleConvertText} className='converttotext' icon='icon-text'><Trans id='js.table.ColumnContextMenu.convertToText'>Convert to text</Trans></DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleFormatNumbers} className='formatnumbers' icon='icon-number' disabled={columnType !== 'number'}><Trans id='js.table.ColumnContextMenu.formatNumbers'>Format numbers</Trans></DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={this.handleDropColumn} className='drop-column' icon='icon-removec'><Trans id='js.table.ColumnContextMenu.deleteColumn'>Delete column</Trans></DropdownItem>
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}
