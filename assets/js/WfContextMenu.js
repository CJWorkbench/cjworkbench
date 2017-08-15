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
    this.deleteOption = this.deleteOption.bind(this);
    this.shareOption = this.shareOption.bind(this);
  }

  deleteOption() {
    this.props.deleteWorkflow();
  }

  // This prop currently does not exist in the parent class
  shareOption() {
    this.props.shareWorkflow();
  }

  render() {
    return (
       <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <div className='button-icon icon-more'></div>
        </DropdownToggle>
        <DropdownMenu right className='dropdown-menu'>
          <DropdownItem key={1} onClick={this.shareOption} className='dropdown-menu-item test-share-button'>
            <i className="icon-share button-icon"></i>
            <span className='t-d-gray content-3 ml-3'>Share</span>
          </DropdownItem>
          {/* Will delete the parent Workflow from the Workflows List */}
          <DropdownItem key={2} onClick={this.deleteOption} className='dropdown-menu-item test-delete-button'>
            <i className="icon-bin button-icon"></i>
            <span className='t-d-gray content-3 ml-3'>Delete</span>
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WfContextMenu.propTypes = {
  deleteWorkflow: PropTypes.func
};
