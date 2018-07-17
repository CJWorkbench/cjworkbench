// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import PropTypes from 'prop-types'
import Portal from 'reactstrap/lib/Portal'
import UncontrolledDropdown from 'reactstrap/lib/UncontrolledDropdown'
import DropdownToggle from 'reactstrap/lib/DropdownToggle'
import DropdownMenu from 'reactstrap/lib/DropdownMenu'
import DropdownItem from 'reactstrap/lib/DropdownItem'
import { sortDirectionNone, sortDirectionAsc, sortDirectionDesc} from './SortFromTable'

export default class ColumnContextMenu extends React.Component {
  static propTypes = {
    setSortDirection: PropTypes.func.isRequired,
    sortDirection: PropTypes.oneOf([sortDirectionNone, sortDirectionAsc, sortDirectionDesc]).isRequired
  }

  setSortDirectionNone = () => this.props.setSortDirection(sortDirectionNone)
  setSortDirectionAsc = () => this.props.setSortDirection(sortDirectionAsc)
  setSortDirectionDesc = () => this.props.setSortDirection(sortDirectionDesc)


  render() {
    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='icon-more'></i>
        </DropdownToggle>
        <Portal>
          <DropdownMenu persist flip={false} modifiers={{preventOverflow: {enabled: false}}}>
            {/* <DropdownItem onClick={this.setSortDirectionNone} className='test-sort-none'>
              {this.props.sortDirection == sortDirectionNone ? <i className='icon-check' /> : null}
              <span>Not Sorted</span>
            </DropdownItem> */}
            {/* <DropdownItem divider /> */}
            <DropdownItem onClick={this.setSortDirectionAsc} className='test-sort-ascending'>
              {this.props.sortDirection == sortDirectionAsc ? <i className='icon-check' /> : null}
              <i className="icon-check"></i>
              <span>Sort Ascending</span>

            </DropdownItem>
            <DropdownItem onClick={this.setSortDirectionDesc} className='test-sort-descending'>
              {this.props.sortDirection == sortDirectionDesc ? <i className='icon-check' /> : null}
              <i className="icon-check"></i>
              <span>Sort Descending</span>
            </DropdownItem>
          </DropdownMenu>
        </Portal>
      </UncontrolledDropdown>
    );
  }
}
