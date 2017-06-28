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
import CopyToClipboard from 'react-copy-to-clipboard';


export default class WorkflowModuleContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.deleteOption = this.deleteOption.bind(this);
    this.toggleExportModal = this.toggleExportModal.bind(this);
    this.renderExportModal = this.renderExportModal.bind(this);    
    this.onCsvCopy = this.onCsvCopy.bind(this);  
    this.onJsonCopy = this.onJsonCopy.bind(this);                  
    this.state = {
      exportModalOpen: false, 
      csvCopied: false,
      jsonCopied: false
    };           
  }
  
  deleteOption() {
    this.props.removeModule();
  }

  toggleExportModal() {
    this.setState({ exportModalOpen: !this.state.exportModalOpen });
  }

  csvUrlString(id) {
    return '/public/moduledata/live/' + id + '.csv';
  }

  jsonUrlString(id) {
    return '/public/moduledata/live/' + id + '.json';
  }

  onCsvCopy() {
    this.setState({csvCopied: true});
  }

  onJsonCopy() {
    this.setState({jsonCopied: true});
  }

  // To Fix: Does not change text after clicking on copy link
  renderCsvCopyLink() {
    var csvString = this.csvUrlString(this.props.id);    

    if (this.state.copied) {
      return (
        <div style={{color: 'red'}}>CSV link copied to clipboard</div>
      );
    } else {
      return (
        <CopyToClipboard text={csvString} onCopy={this.onCsvCopy}>
          <div>Copy live CSV link</div>
        </CopyToClipboard>
      );
    }
  }

  // To Fix: Does not change text after clicking on copy link  
  renderJsonCopyLink() {
    var jsonString = this.jsonUrlString(this.props.id);    

    if (this.state.copied) {
      return (
        <div style={{color: 'red'}}>JSON link copied to clipboard</div>
      );
    } else {
      return (
        <CopyToClipboard text={jsonString} onCopy={this.onJsonCopy}>
          <div>Copy live JSON link</div>
        </CopyToClipboard>
      );
    }
  }

  renderExportModal() {
    if (!this.state.exportModalOpen) {
      return null;
    }

    var csvString = this.csvUrlString(this.props.id);    
    var jsonString = this.jsonUrlString(this.props.id);    
    var csvCopyLink = this.renderCsvCopyLink();
    var jsonCopyLink = this.renderJsonCopyLink();

    return (
      <Modal isOpen={this.state.exportModalOpen} toggle={this.toggleExportModal} className={this.props.className}>
        <ModalHeader toggle={this.toggleModal}>Export Data</ModalHeader>
        <ModalBody>
          <FormGroup>
            <Label for="exampleText">CSV</Label>
            {csvCopyLink}
            <Input type="url" name="url" id="csvUrl" placeholder={csvString}/>
            <Label for="exampleText">JSON</Label>
            {jsonCopyLink}
            <Input type="url" name="url" id="jsonUrl" placeholder={jsonString}/>
          </FormGroup>
        </ModalBody>
        <ModalFooter>
          <Button color='primary' onClick={this.toggleExportModal}>Done</Button>{' '}
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
  removeModule: PropTypes.func,
  id:           PropTypes.number
};

