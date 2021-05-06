// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import { Component } from 'react'
import PropTypes from 'prop-types'
import {
  UncontrolledDropdown,
  DropdownMenu,
  DropdownToggle,
  DropdownItem,
  DropdownDivider
} from '../components/Dropdown'
import { Trans } from '@lingui/macro'

const ColumnConverters = {
  text: {
    number: 'converttexttonumber',
    date: 'converttexttodate',
    timestamp: 'convert-date', // FIXME rename module
    text: null
  },
  number: {
    text: 'converttotext',
    date: null,
    timestamp: null,
    number: null
  },
  date: {
    text: 'converttotext',
    date: 'convertdatetodate', // special case!
    timestamp: null,
    number: null
  },
  timestamp: {
    text: 'converttotext',
    date: 'converttimestamptodate',
    timestamp: null,
    number: null
  }
}

export default class ColumnContextMenu extends Component {
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

  handleAddNewFilter = () => this.create('filter')
  handleCleanText = () => this.createOrUpdate('clean-text')
  handleConvert = ev => this.createOrUpdate(ev.target.value)
  handleDropColumn = () => this.createOrUpdate('selectcolumns', { keep: false })
  handleDuplicateColumn = () => this.createOrUpdate('duplicatecolumns')
  handleFormatNumbers = () => this.create('formatnumbers', { format: '{:,}' })
  handleRenameColumn = (...args) => this.props.renameColumn(...args)
  handleSortAscending = () => this.createOrUpdate('sort', { is_ascending: true })
  handleSortDescending = () => this.createOrUpdate('sort', { is_ascending: false })

  render () {
    const { columnType } = this.props

    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='icon-caret-down' />
        </DropdownToggle>
        <DropdownMenu>
          <DropdownItem
            onClick={this.handleRenameColumn}
            className='rename-column-header'
            icon='icon-edit'
          >
            <Trans id='js.table.ColumnContextMenu.rename.'>Rename</Trans>
          </DropdownItem>
          <DropdownItem
            onClick={this.handleDuplicateColumn}
            className='duplicatecolumns'
            icon='icon-duplicate'
          >
            <Trans id='js.table.ColumnContextMenu.duplicate'>Duplicate</Trans>
          </DropdownItem>
          <DropdownDivider />
          <DropdownItem
            onClick={this.handleSortAscending}
            className='sort-ascending'
            icon='icon-sort-up'
          >
            <Trans id='js.table.ColumnContextMenu.sortAscending'>
              Sort ascending
            </Trans>
          </DropdownItem>
          <DropdownItem
            onClick={this.handleSortDescending}
            className='sort-descending'
            icon='icon-sort-down'
          >
            <Trans id='js.table.ColumnContextMenu.sortDescending'>
              Sort descending
            </Trans>
          </DropdownItem>
          <DropdownDivider />
          <DropdownItem
            onClick={this.handleAddNewFilter}
            className='filter-column'
            icon='icon-filter'
          >
            <Trans id='js.table.ColumnContextMenu.filter'>Filter</Trans>
          </DropdownItem>
          <DropdownItem
            onClick={this.handleCleanText}
            className='clean-text'
            icon='icon-clean'
          >
            <Trans id='js.table.ColumnContextMenu.cleanText'>Clean Text</Trans>
          </DropdownItem>

          <DropdownDivider />

          <DropdownItem
            onClick={this.handleConvert}
            value={ColumnConverters[columnType].date || ''}
            disabled={ColumnConverters[columnType].date === null}
            icon='icon-calendar'
          >
            {columnType === 'date'
              ? (
                <Trans id='js.table.ColumnContextMenu.convertDateUnit'>
                  Convert date unit
                </Trans>
                )
              : (
                <Trans id='js.table.ColumnContextMenu.convertToDate'>
                  Convert to date
                </Trans>
                )}
          </DropdownItem>
          <DropdownItem
            onClick={this.handleConvert}
            value={ColumnConverters[columnType].number || ''}
            disabled={ColumnConverters[columnType].number === null}
            icon='icon-number'
          >
            <Trans id='js.table.ColumnContextMenu.convertToNumbers'>
              Convert to number
            </Trans>
          </DropdownItem>
          <DropdownItem
            onClick={this.handleConvert}
            value={ColumnConverters[columnType].text || ''}
            disabled={ColumnConverters[columnType].text === null}
            icon='icon-text'
          >
            <Trans id='js.table.ColumnContextMenu.convertToText'>
              Convert to text
            </Trans>
          </DropdownItem>
          <DropdownItem
            onClick={this.handleConvert}
            value={ColumnConverters[columnType].timestamp || ''}
            disabled={ColumnConverters[columnType].timestamp === null}
            icon='icon-calendar'
          >
            <Trans id='js.table.ColumnContextMenu.convertToTimestamp'>
              Convert to timestamp
            </Trans>
          </DropdownItem>

          <DropdownDivider />

          <DropdownItem
            onClick={this.handleFormatNumbers}
            className='formatnumbers'
            icon='icon-number'
            disabled={columnType !== 'number'}
          >
            <Trans id='js.table.ColumnContextMenu.formatNumbers'>
              Format numbers
            </Trans>
          </DropdownItem>

          <DropdownDivider />

          <DropdownItem
            onClick={this.handleDropColumn}
            className='drop-column'
            icon='icon-removec'
          >
            <Trans id='js.table.ColumnContextMenu.deleteColumn'>
              Delete column
            </Trans>
          </DropdownItem>
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}
