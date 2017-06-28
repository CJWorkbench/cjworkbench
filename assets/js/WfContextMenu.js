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

  // \u22EE = three-dot menu icon in Unicode 
  render() {
    return (
       <UncontrolledDropdown>
        <DropdownToggle className='context-menu-icon'>
          {'\u22EE'}
        </DropdownToggle>
        <DropdownMenu right >
          {/* Will delete the parent Workflow from the Workflows List */}
          <DropdownItem key={1} onClick={this.deleteOption}>                       
            Delete 
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WfContextMenu.propTypes = {
  deleteWorkflow: PropTypes.func  
};

