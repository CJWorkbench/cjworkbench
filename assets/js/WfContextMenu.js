// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import {
  UncontrolledDropdown,
  DropdownToggle,
  DropdownMenu,
  DropdownItem
} from 'reactstrap'
import PropTypes from 'prop-types'


export default class WfContextMenu extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
       <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <div className='context-button--icon icon-more'></div>
        </DropdownToggle>
        <DropdownMenu right className='dropdown-menu'>
          <DropdownItem key={2} onClick={this.props.duplicateWorkflow} className='dropdown-menu-item test-duplicate-button'>
            <i className="icon-duplicate context-menu--item-icon"></i>
            <span className='t-d-gray content-3 ml-3'>Duplicate</span>
          </DropdownItem>
          <DropdownItem key={3} onClick={this.props.deleteWorkflow} className='dropdown-menu-item test-delete-button'>
            <i className="icon-bin context-menu--item-icon"></i>
            <span className='t-d-gray content-3 ml-3'>Delete</span>
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WfContextMenu.propTypes = {
  deleteWorkflow:     PropTypes.func.isRequired,
  duplicateWorkflow:  PropTypes.func.isRequired
};
