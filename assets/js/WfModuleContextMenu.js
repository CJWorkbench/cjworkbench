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


export default class WfModuleContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.deleteOption = this.deleteOption.bind(this);
    this.toggleExportModal = this.toggleExportModal.bind(this);
    this.renderExportModal = this.renderExportModal.bind(this);    
    this.onCsvCopy = this.onCsvCopy.bind(this);  
    this.onCsvLeave = this.onCsvLeave.bind(this);      
    this.onJsonCopy = this.onJsonCopy.bind(this); 
    this.onJsonLeave = this.onJsonLeave.bind(this);                           
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

  // Code Smell: Repitition between CSV and JSON methods, target for DRY refactoring

  csvUrlString(id) {
    var path = "/public/moduledata/live/" + id + ".csv";
    var url = new URL(path, window.location.href).href;
    return url;
  }

  jsonUrlString(id) {
    var path = "/public/moduledata/live/" + id + ".json";
    var url = new URL(path, window.location.href).href;
    return url;
  }

  onCsvCopy() {
    this.setState({csvCopied: true});
  }

  onCsvLeave() {
    this.setState({csvCopied: false});
  }

  onJsonCopy() {
    this.setState({jsonCopied: true});
  }

  onJsonLeave() {
    this.setState({jsonCopied: false});
  }

  renderCsvCopyLink() {
    var csvString = this.csvUrlString(this.props.id);    

    if (this.state.csvCopied) {
      return (
        <div style={{color: 'red'}} onMouseLeave={this.onCsvLeave}>CSV link copied to clipboard</div>
      );
    } else {
      return (
        <CopyToClipboard text={csvString} onCopy={this.onCsvCopy}>
          <div>Copy live CSV link</div>
        </CopyToClipboard>
      );
    }
  }

  renderJsonCopyLink() {
    var jsonString = this.jsonUrlString(this.props.id);    

    if (this.state.jsonCopied) {
      return (
        <div style={{color: 'red'}} onMouseLeave={this.onCsvLeave}>JSON link copied to clipboard</div>
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

    // '\u2193' is a Unicode down-arrow
    return (
      <Modal isOpen={this.state.exportModalOpen} toggle={this.toggleExportModal} className={this.props.className}>
        <ModalHeader toggle={this.toggleModal}>Export Data</ModalHeader>
        <ModalBody>
          <FormGroup>
            <Label for="exampleText">CSV</Label>
            {csvCopyLink}
            <a href={csvString} download>{'\u2193'}</a>
            <Input type="url" placeholder={csvString} readOnly/>
            <Label for="exampleText">JSON</Label>
            {jsonCopyLink}
            <a href={jsonString} download>{'\u2193'}</a>            
            <Input type="url" placeholder={jsonString} readOnly/>
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

WfModuleContextMenu.propTypes = {
  removeModule: PropTypes.func,
  id:           PropTypes.number
};

