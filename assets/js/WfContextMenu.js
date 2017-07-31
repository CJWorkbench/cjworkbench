// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap'
import PropTypes from 'prop-types'


export default class WfContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.deleteOption = this.deleteOption.bind(this);
  }

  deleteOption() {
    this.props.deleteWorkflow();
  }

  shareOption() {
    this.props.shareWorkflow();
  }

  // \u22EE = three-dot menu icon in Unicode
  render() {
    return (
       <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <div className='button-icon icon-more'></div>
        </DropdownToggle>
        <DropdownMenu >
          {/* Will delete the parent Workflow from the Workflows List */}
          <DropdownItem key={1} onClick={this.deleteOption} className='dropdown-menu-item'>
            <span className='t-d-gray content-3 ml-3'>Delete</span>
          </DropdownItem>
          <DropdownItem key={2} onClick={this.shareOption}>
            <span className='t-d-gray content-3 ml-3'>Share</span>
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WfContextMenu.propTypes = {
  deleteWorkflow: PropTypes.func
};
