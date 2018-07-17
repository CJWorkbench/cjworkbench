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
            <DropdownItem onClick={this.setSortDirectionAsc} className='sort-ascending'>
              <i className="icon-sort-up"></i>
              <span>Sort ascending</span>
            </DropdownItem>
            <DropdownItem onClick={this.setSortDirectionDesc} className='sort-descending'>
              <i className="icon-sort-down"></i>
              <span>Sort descending</span>
            </DropdownItem>
          </DropdownMenu>
        </Portal>
      </UncontrolledDropdown>
    );
  }
}
