// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react';
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap';

export default class WorkflowModuleContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.deleteOption = this.deleteOption.bind(this);
  }
  
  deleteOption() {
    this.props.removeModule();
  }

  // \u22EE = three-dot menu icon in Unicode 
  render() {
    return (
       <UncontrolledDropdown>
        <DropdownToggle>
          {'\u22EE'}
        </DropdownToggle>
        <DropdownMenu right >
          {/* Will delete the parent WF Module from the list */}
          <DropdownItem key={1} onClick={this.deleteOption}>                       
            Delete This Module
          </DropdownItem>
          {/* second menu item currently does nothing */}
          <DropdownItem key={2}>                       
            Export Table
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WorkflowModuleContextMenu.propTypes = {
  removeModule: React.PropTypes.func  
};

