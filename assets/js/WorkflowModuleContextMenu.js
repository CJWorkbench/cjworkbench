// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

// To refactor: shorten module name, change references

import React from 'react'
import { 
    Button,
    UncontrolledDropdown, 
    DropdownToggle, 
    DropdownMenu, 
    DropdownItem, 
    Modal, 
    ModalHeader, 
    ModalBody, 
    ModalFooter,
    Form, 
    FormGroup, 
    Label, 
    Input
  } from 'reactstrap'
import PropTypes from 'prop-types'


export default class WorkflowModuleContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.deleteOption = this.deleteOption.bind(this);
    this.toggleExportModal = this.toggleExportModal.bind(this);
    this.renderExportModal = this.renderExportModal.bind(this);    
    this.state = {exportModalOpen: false};           // Export pop-up starts closed
  }
  
  deleteOption() {
    this.props.removeModule();
  }

  toggleExportModal() {
    this.setState({ exportModalOpen: !this.state.exportModalOpen });
  }

  renderExportModal() {
    if (!this.state.exportModalOpen) {
      return null;
    }

    // Copied from Navbar Modal, needs revision 
    return (
      <Modal isOpen={this.state.exportModalOpen} toggle={this.toggleExportModal} className={this.props.className}>
        <ModalHeader toggle={this.toggleModal}>External Data Settings</ModalHeader>
        <ModalBody>
          <FormGroup>
            <Label for="exampleSelect">Which version?</Label>
            <Input type="select" name="select" id="exampleSelect" className="mb-3">
              <option>Most Recent</option>
              <option value="" disabled="disabled">──────────</option>
              <option>April 28 at 4:40PM </option>
              <option>April 28 at 10:32AM </option>
              <option>April 26 at 6:06PM</option>
              <option>April 12 at 2:51PM</option>
            </Input>
            <Label for="exampleSelect2">Update when?</Label>
            <Input type="select" name="select" id="exampleSelect2">
              <option>Manual only</option>
              <option value="" disabled="disabled">──────────</option>
              <option>Every minute</option>
              <option>Every five minutes</option>
              <option>Hourly</option>
              <option>Daily</option>
              <option>Weekly</option>
            </Input>
          </FormGroup>
        </ModalBody>
        <ModalFooter>
          <Button color='primary' onClick={this.toggleExportModal}>Ok</Button>{' '}
          <Button color='secondary' onClick={this.toggleExportModal}>Cancel</Button>
        </ModalFooter>
      </Modal>
    );
  }

  // \u22EE = three-dot menu icon in Unicode 
  render() {
    var exportModal = this.renderExportModal();

    return (
       <UncontrolledDropdown>
        <DropdownToggle className='context-menu-icon'>
          {'\u22EE'}
        </DropdownToggle>
        <DropdownMenu right >
          {/* Will delete the parent WF Module from the list */}
          <DropdownItem key={1} onClick={this.deleteOption}>                       
            Delete This Module
          </DropdownItem>
          {/* Opens Modal window for downloading files */}
          <DropdownItem key={2} onClick={this.toggleExportModal}>                       
            Export Table
            {exportModal}
          </DropdownItem>
          {/* further menu items currently do nothing */}          
          <DropdownItem key={3}>                       
            Update Version
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WorkflowModuleContextMenu.propTypes = {
  removeModule: PropTypes.func  
};

