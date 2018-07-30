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
    duplicateColumn:  PropTypes.func.isRequired,
    dropColumn:       PropTypes.func.isRequired,
    filterColumn:     PropTypes.func.isRequired,
    renameColumn:     PropTypes.func.isRequired,
    setSortDirection: PropTypes.func.isRequired,
    sortDirection:    PropTypes.oneOf([sortDirectionNone, sortDirectionAsc, sortDirectionDesc]).isRequired
  }

  setSortDirectionAsc = () => this.props.setSortDirection(sortDirectionAsc)
  setSortDirectionDesc = () => this.props.setSortDirection(sortDirectionDesc)


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
            <DropdownItem onClick={this.props.duplicateColumn} className='duplicate-column' toggle={false}>
              <i className="icon-duplicate"></i>
              <span>Duplicate</span>
            </DropdownItem>
            <DropdownItem divider />
            <DropdownItem onClick={this.setSortDirectionAsc} className='sort-ascending' toggle={false}>
              <i className="icon-sort-up"></i>
              <span>Sort ascending</span>
            </DropdownItem>
            <DropdownItem onClick={this.setSortDirectionDesc} className='sort-descending' toggle={false}>
              <i className="icon-sort-down"></i>
              <span>Sort descending</span>
            </DropdownItem>
            <DropdownItem divider />
            <DropdownItem onClick={this.props.filterColumn} className='filter-column' toggle={false}>
              <i className="icon-filter"></i>
              <span>Filter</span>
            </DropdownItem>
            <DropdownItem onClick={this.props.dropColumn} className='drop-column' toggle={false}>
              <i className="icon-removec"></i>
              <span>Drop column</span>
            </DropdownItem>
          </DropdownMenu>
        </Portal>
      </UncontrolledDropdown>
    );
  }
}
