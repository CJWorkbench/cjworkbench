import React from 'react'
import PropTypes from 'prop-types'
import CopyToClipboard from 'react-copy-to-clipboard'
import { logUserEvent } from './utils'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './components/Modal'

export default class ExportModal extends React.PureComponent {
  static propTypes = {
    open: PropTypes.bool.isRequired,
    wfModuleId: PropTypes.number.isRequired, // to build download URLs
    toggle: PropTypes.func.isRequired
  }

  state = {
    csvCopied: false,
    jsonCopied: false,
  }

  buildUrlString (ext) {
    const path = `/public/moduledata/live/${this.props.wfModuleId}.${ext}`
    if (window.location.href === 'about:blank') {
      // allowing an out for testing (there is no window.location.href during test)
      return path
    } else {
      return new URL(path, window.location.href).href
    }
  }

  get csvUrlString () {
    return this.buildUrlString('csv')
  }

  get jsonUrlString () {
    return this.buildUrlString('json')
  }

  handleCopyCsv = () => {
    this.setState({ csvCopied: true })
  }

  handleLeaveCsv = () => {
    this.setState({ csvCopied: false })
  }

  handleCopyJson = () => {
    this.setState({ jsonCopied: true })
  }

  handleLeaveJson = () => {
    this.setState({ jsonCopied: false })
  }

  logExport (type) {
    logUserEvent('Export ' + type)
  }

  renderCsvCopyLink () {
    if (this.state.csvCopied) {
      return (
        <div className='clipboard copied' onMouseLeave={this.handleLeaveCsv}>CSV LINK COPIED TO CLIPBOARD</div>
      )
    } else {
      return (
        <CopyToClipboard text={this.csvUrlString} onCopy={this.handleCopyCsv} className='clipboard test-csv-copy'>
          <div>COPY LIVE LINK</div>
        </CopyToClipboard>
      )
    }
  }

  renderJsonCopyLink () {
    if (this.state.jsonCopied) {
      return (
        <div className='clipboard copied' onMouseLeave={this.handleLeaveJson}>JSON FEED LINK COPIED TO CLIPBOARD</div>
      )
    } else {
      return (
        <CopyToClipboard text={this.jsonUrlString} onCopy={this.handleCopyJson} className='clipboard test-json-copy'>
          <div>COPY LIVE LINK</div>
        </CopyToClipboard>
      )
    }
  }

  render () {
    const csvCopyLink = this.renderCsvCopyLink()
    const jsonCopyLink = this.renderJsonCopyLink()

    return (
      <Modal isOpen={this.props.open} className={this.props.className} toggle={this.props.toggle}>
        <ModalHeader>EXPORT DATA</ModalHeader>
        <ModalBody>
          <div className='d-flex justify-content-between flex-row'>
            <div className='dl-file'>CSV</div>
            {csvCopyLink}
          </div>
          <div className='d-flex justify-content-between flex-row mb-3'>
            <input type='url' className='url-link test-csv-field' value={this.csvUrlString} readOnly />
            <div className='download-icon-box'>
              <a
                href={this.csvUrlString} onClick={() => this.logExport('CSV')}
                className='icon-download t-d-gray button-icon test-csv-download' download
              />
            </div>
          </div>
          <div className='d-flex justify-content-between flex-row'>
            <div className='dl-file'>JSON FEED</div>
            {jsonCopyLink}
          </div>
          <div className='d-flex justify-content-between flex-row'>
            <input type='url' className='url-link test-json-field' value={this.jsonUrlString} readOnly />
            <div className='download-icon-box'>
              <a
                href={this.jsonUrlString} onClick={() => this.logExport('JSON')}
                className='icon-download t-d-gray button-icon test-json-download' download
              />
            </div>
          </div>
        </ModalBody>
        <ModalFooter>
          <button type='button' onClick={this.props.toggle} className='button-blue action-button test-done-button'>Done</button>
        </ModalFooter>
      </Modal>
    )
  }
}
