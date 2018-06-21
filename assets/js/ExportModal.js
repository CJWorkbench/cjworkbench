import React from "react";
import PropTypes from 'prop-types'
import CopyToClipboard from 'react-copy-to-clipboard';
import {logUserEvent} from "./utils";
import Modal from 'reactstrap/lib/Modal'
import ModalHeader from 'reactstrap/lib/ModalHeader'
import ModalBody from 'reactstrap/lib/ModalBody'
import ModalFooter from 'reactstrap/lib/ModalFooter'
import FormGroup from 'reactstrap/lib/FormGroup'
import Label from 'reactstrap/lib/Label'
import Input from 'reactstrap/lib/Input'


export default class ExportModal extends React.Component {
  static propTypes = {
    open:       PropTypes.bool.isRequired,
    wfModuleId: PropTypes.number.isRequired, // to build download URLs
    onClose:    PropTypes.func.isRequired,
  };

  constructor(props) {
    super(props);

    this.onCsvCopy = this.onCsvCopy.bind(this);
    this.onCsvLeave = this.onCsvLeave.bind(this);
    this.onJsonCopy = this.onJsonCopy.bind(this);
    this.onJsonLeave = this.onJsonLeave.bind(this);
    this.logExport = this.logExport.bind(this);

    this.state = {
      csvCopied: false,
      jsonCopied: false
    }
  }


  csvUrlString() {
    var path = "/public/moduledata/live/" + this.props.wfModuleId + ".csv";
    // allowing an out for testing (there is no window.location.href during test)
    if (window.location.href == 'about:blank') {
      return path;
    } else {
      return new URL(path, window.location.href).href;
    }
  }

  jsonUrlString() {
    var path = "/public/moduledata/live/" + this.props.wfModuleId + ".json";
    // allowing an out for testing (there is no window.location.href during test)
    if (window.location.href == 'about:blank') {
      return path;
    } else {
      return new URL(path, window.location.href).href;
    }
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

  logExport(type) {
    logUserEvent('Export ' + type)
  }

  renderCsvCopyLink() {
    var csvString = this.csvUrlString(this.props.wfModuleId);

    if (this.state.csvCopied) {
      return (
        <div className='info-2 t-orange mt-3' onMouseLeave={this.onCsvLeave}>CSV LINK COPIED TO CLIPBOARD</div>
      );
    } else {
      return (
        <CopyToClipboard text={csvString} onCopy={this.onCsvCopy} className='info-1 action-link test-csv-copy'>
          <div>COPY LIVE LINK</div>
        </CopyToClipboard>
      );
    }
  }

  renderJsonCopyLink() {
    var jsonString = this.jsonUrlString(this.props.wfModuleId);

    if (this.state.jsonCopied) {
      return (
        <div className='info-2 t-orange mt-3' onMouseLeave={this.onJsonLeave}>JSON LINK COPIED TO CLIPBOARD</div>
      );
    } else {
      return (
        <CopyToClipboard text={jsonString} onCopy={this.onJsonCopy} className='info-1 action-link test-json-copy'>
          <div>COPY LIVE LINK</div>
        </CopyToClipboard>
      );
    }
  }

  render () {
    if (!this.props.open)
      return null;

    var csvString = this.csvUrlString(this.props.wfModuleId);
    var jsonString = this.jsonUrlString(this.props.wfModuleId);
    var csvCopyLink = this.renderCsvCopyLink();
    var jsonCopyLink = this.renderJsonCopyLink();

    return (
      <Modal isOpen={true} className={this.props.className}>
        <ModalHeader className='dialog-header modal-header d-flex align-items-center'>
          <div className='modal-title'>EXPORT DATA</div>
          <div className='icon-close' onClick={this.props.onClose}></div>
        </ModalHeader>
        <ModalBody>
          <FormGroup>
            <div className='d-flex justify-content-between flex-row'>
              <Label className='t-d-gray info-1'>CSV</Label>
              {csvCopyLink}
            </div>
            <div className='d-flex justify-content-between flex-row mb-3'>
              <Input type='url' className='url-link t-d-gray content-2 test-csv-field' value={csvString}
                     readOnly/>
              <div className='download-icon-box'>
                <a href={csvString} onClick={() => this.logExport('CSV')}
                   className='icon-download t-d-gray button-icon test-csv-download' download></a>
              </div>
            </div>
            <div className='d-flex justify-content-between flex-row'>
              <Label className='t-d-gray info-1'>JSON</Label>
              {jsonCopyLink}
            </div>
            <div className='d-flex justify-content-between flex-row'>
              <Input type='url' className='url-link t-d-gray content-2 test-json-field' value={jsonString}
                     readOnly/>
              <div className='download-icon-box'>
                <a href={jsonString} onClick={() => this.logExport('JSON')}
                   className='icon-download t-d-gray button-icon test-json-download' download></a>
              </div>
            </div>
          </FormGroup>
        </ModalBody>
        <ModalFooter>
          <button onClick={this.props.onClose} className='button-blue action-button test-done-button'>Done</button>
          {' '}
        </ModalFooter>
      </Modal>
    );
  }

}
