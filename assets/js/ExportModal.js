import React from 'react'
import PropTypes from 'prop-types'
import CopyToClipboard from 'react-copy-to-clipboard'
import { logUserEvent } from './utils'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './components/Modal'
import { FormGroup, Label, Input } from './components/Form'

export default class ExportModal extends React.Component {
  static propTypes = {
    open:       PropTypes.bool.isRequired,
    wfModuleId: PropTypes.number.isRequired, // to build download URLs
    toggle:    PropTypes.func.isRequired,
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
        <div className='clipboard copied' onMouseLeave={this.onCsvLeave}>CSV LINK COPIED TO CLIPBOARD</div>
      );
    } else {
      return (
        <CopyToClipboard text={csvString} onCopy={this.onCsvCopy} className='clipboard test-csv-copy'>
          <div>COPY LIVE LINK</div>
        </CopyToClipboard>
      );
    }
  }

  renderJsonCopyLink() {
    var jsonString = this.jsonUrlString(this.props.wfModuleId);

    if (this.state.jsonCopied) {
      return (
        <div className='clipboard copied' onMouseLeave={this.onJsonLeave}>JSON FEED LINK COPIED TO CLIPBOARD</div>
      );
    } else {
      return (
        <CopyToClipboard text={jsonString} onCopy={this.onJsonCopy} className='clipboard test-json-copy'>
          <div>COPY LIVE LINK</div>
        </CopyToClipboard>
      );
    }
  }

  render () {
    const csvString = this.csvUrlString(this.props.wfModuleId);
    const jsonString = this.jsonUrlString(this.props.wfModuleId);
    const csvCopyLink = this.renderCsvCopyLink();
    const jsonCopyLink = this.renderJsonCopyLink();

    return (
      <Modal isOpen={this.props.open} className={this.props.className} toggle={this.props.toggle}>
        <ModalHeader>EXPORT DATA</ModalHeader>
        <ModalBody>
          <FormGroup>
            <div className='d-flex justify-content-between flex-row'>
              <Label className='dl-file'>CSV</Label>
              {csvCopyLink}
            </div>
            <div className='d-flex justify-content-between flex-row mb-3'>
              <Input type='url' className='url-link test-csv-field' value={csvString}
                     readOnly/>
              <div className='download-icon-box'>
                <a href={csvString} onClick={() => this.logExport('CSV')}
                   className='icon-download t-d-gray button-icon test-csv-download' download></a>
              </div>
            </div>
            <div className='d-flex justify-content-between flex-row'>
              <Label className='dl-file'>JSON FEED</Label>
              {jsonCopyLink}
            </div>
            <div className='d-flex justify-content-between flex-row'>
              <Input type='url' className='url-link test-json-field' value={jsonString}
                     readOnly/>
              <div className='download-icon-box'>
                <a href={jsonString} onClick={() => this.logExport('JSON')}
                   className='icon-download t-d-gray button-icon test-json-download' download></a>
              </div>
            </div>
          </FormGroup>
        </ModalBody>
        <ModalFooter>
          <button type='button' onClick={this.props.toggle} className='button-blue action-button test-done-button'>Done</button>
        </ModalFooter>
      </Modal>
    )
  }

}
