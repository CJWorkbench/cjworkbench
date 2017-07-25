// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow module

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
        <div className='info-small-orange' onMouseLeave={this.onCsvLeave}>CSV link copied to clipboard</div>
      );
    } else {
      return (
        <CopyToClipboard text={csvString} onCopy={this.onCsvCopy} className='info-small-blue'>
          <div>Copy live link</div>
        </CopyToClipboard>
      );
    }
  }

  renderJsonCopyLink() {
    var jsonString = this.jsonUrlString(this.props.id);    

    if (this.state.jsonCopied) {
      return (
        <div className='info-small-orange' onMouseLeave={this.onJsonLeave}>JSON link copied to clipboard</div>
      );
    } else {
      return (
        <CopyToClipboard text={jsonString} onCopy={this.onJsonCopy} className='info-small-blue'> 
          <div>Copy live link</div>
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

    // TODO: Normalize class names
    return (
      <Modal isOpen={this.state.exportModalOpen} toggle={this.toggleExportModal} className={this.props.className}>
        <ModalHeader toggle={this.toggleModal} className='dialog-header' >
          <span className='dialog-box-title-gray'>Export Data</span>
          <span className='icon-close dialog-header-close' onClick={this.toggleExportModal}></span> 
        </ModalHeader>
        <ModalBody className='dialog-body'>
          <FormGroup>
            <div className='export-field-header'>
              <Label className='title-line-item-gray'>CSV</Label>
              <div className='export-link'>{csvCopyLink}</div>
            </div>     
            <div className='export-field'>            
              <Input type='url' className='data-gray text-field' placeholder={csvString} readOnly/>   
              <div className='export-icon-box'>                              
                <a href={csvString} className='icon-download' download></a>
              </div>
            </div>
            <div className='export-field-header'>            
              <Label className='title-line-item-gray'>JSON</Label>
              <div className='export-link'>{jsonCopyLink}</div>
            </div>
            <div className='export-field'>                        
              <Input type='url' className='data-gray text-field' placeholder={jsonString} readOnly/>            
              <div className='export-icon-box'>
                <a href={jsonString} className='icon-download' download></a>    
              </div>
            </div>        
          </FormGroup>
        </ModalBody>
        <ModalFooter className='dialog-footer'>
          <Button onClick={this.toggleExportModal} className='button-blue action-button'>Done</Button>{' '}
        </ModalFooter>
      </Modal>
    );
  }

  render() {
    var exportModal = this.renderExportModal();

    return (
       <UncontrolledDropdown onClick={this.props.stopProp}>
        <DropdownToggle className='context-button text-center p-0'>
          <div className='button-icon icon-more'></div>
        </DropdownToggle>
        <DropdownMenu right className='dropdown-list-menu'>
          {/* Opens Modal window for downloading files */}
          <DropdownItem key={1} onClick={this.toggleExportModal} className='dropdown-list-item'>                       
            <span className='icon-download icon-w mr-2'></span>
            <span className='setting-gray'>Export</span>
            {exportModal}
          </DropdownItem>
          {/* Currently does nothing */}          
          <DropdownItem key={2} className='dropdown-list-item'>      
            <span className='icon-info icon-w mr-2'></span>                             
            <span className='setting-gray'>Update</span>
          </DropdownItem>
          {/* Will delete the parent WF Module from the list */}
          <DropdownItem key={3} onClick={this.deleteOption} className='dropdown-list-item'>    
            <span className='icon-bin icon-w mr-2'></span>                               
            <span className='setting-gray'>Delete</span>
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WfModuleContextMenu.propTypes = {
  removeModule: PropTypes.func,
  id:           PropTypes.number,
  stopProp:     PropTypes.func
};

