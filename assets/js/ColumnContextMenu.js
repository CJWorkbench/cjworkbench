// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import PropTypes from 'prop-types'
import Portal from 'reactstrap/lib/Portal'
import UncontrolledDropdown from 'reactstrap/lib/UncontrolledDropdown'
import DropdownToggle from 'reactstrap/lib/DropdownToggle'
import DropdownMenu from 'reactstrap/lib/DropdownMenu'
import DropdownItem from 'reactstrap/lib/DropdownItem'
import { sortDirectionNone, sortDirectionAsc, sortDirectionDesc} from './UpdateTableAction'

// Modifiers disabled to prevent menu flipping (occurs even when flip=false)
var dropdownModifiers = {
  preventOverflow: {
    enabled: false
  },
  hide: {
    enabled: false
  }
}

export default class ColumnContextMenu extends React.Component {
  static propTypes = {
    setDropdownAction: PropTypes.func.isRequired,
    columnKey:         PropTypes.string.isRequired,
    columnType:        PropTypes.string.isRequired,
    renameColumn:      PropTypes.func.isRequired,
    sortDirection:     PropTypes.oneOf([sortDirectionNone, sortDirectionAsc, sortDirectionDesc]).isRequired
  }

  // Modules that only need to pass the column name and do not force new modules use setDropdownActionDefault
  setDropdownActionDefault = (idName) => this.props.setDropdownAction(idName, false, {})
  setDropdownActionForceNew = (idName) => this.props.setDropdownAction(idName, true, {})
  setSortDirection (direction) {
    let params = {
      'sortType': this.props.columnType,
      'sortDirection': direction
    }
    this.props.setDropdownAction('sort-from-table', false, params)
  }

  render() {
    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='icon-more'></i>
        </DropdownToggle>
        <Portal>
          <DropdownMenu persist flip={false} modifiers={dropdownModifiers}>
            <DropdownItem onClick={this.props.renameColumn} className='rename-column-header' toggle={false}>
              <i className="icon-edit"></i>
              <span>Rename</span>
            </DropdownItem>
            <DropdownItem onClick={this.setDropdownActionDefault.bind(this, 'duplicate-column')} className='duplicate-column' toggle={false}>
              <i className="icon-duplicate"></i>
              <span>Duplicate</span>
            </DropdownItem>
            <DropdownItem divider />
            <DropdownItem onClick={this.setSortDirection.bind(this, sortDirectionAsc)} className='sort-ascending' toggle={false}>
              <i className="icon-sort-up"></i>
              <span>Sort ascending</span>
            </DropdownItem>
            <DropdownItem onClick={this.setSortDirection.bind(this, sortDirectionDesc)} className='sort-descending' toggle={false}>
              <i className="icon-sort-down"></i>
              <span>Sort descending</span>
            </DropdownItem>
            <DropdownItem divider />
            <DropdownItem onClick={this.setDropdownActionForceNew.bind(this, 'filter')} className='filter-column' toggle={false}>
              <i className="icon-filter"></i>
              <span>Filter</span>
            </DropdownItem>
            <DropdownItem onClick={this.setDropdownActionDefault.bind(this, 'selectcolumns')} className='drop-column' toggle={false}>
              <i className="icon-removec"></i>
              <span>Drop column</span>
            </DropdownItem>
            <DropdownItem onClick={this.setDropdownActionDefault.bind(this, 'extract-numbers')} className='extract-numbers' toggle={false}>
              <i className="icon-number"></i>
              <span>Extract Numbers</span>
            </DropdownItem>
          </DropdownMenu>
        </Portal>
      </UncontrolledDropdown>
    );
  }
}
