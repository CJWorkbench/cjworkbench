// WorkflowMetadata: that line below the workflow title
// which shows owner, last modified date, public/private

import React from 'react'
import PropTypes from 'prop-types'
import Button from 'reactstrap/lib/Button'
import Modal from 'reactstrap/lib/Modal'
import ModalHeader from 'reactstrap/lib/ModalHeader'
import ModalBody from 'reactstrap/lib/ModalBody'
import ModalFooter from 'reactstrap/lib/ModalFooter'
import { timeDifference } from './utils'
import { connect } from 'react-redux'

export default class WorkflowMetadata extends React.Component {
  static propTypes = {
    workflow: PropTypes.object.isRequired,
    onChangeIsPublic: PropTypes.func.isRequired, // func(workflowId, isPublic) => undefined
    test_now: PropTypes.object  // optional injection for testing, avoid time zone issues for Last Update time
  }

  state = {
    privacyModalOpen: false
  }

  onSetWorkflowPublic = () => {
    this.props.onChangeIsPublic(this.props.workflow.id, true)
    this.closePrivacyModal()
  }

  onSetWorkflowPrivate = () => {
    this.props.onChangeIsPublic(this.props.workflow.id, false)
    this.closePrivacyModal()
  }

  openPrivacyModal = (ev) => {
    ev.preventDefault()
    ev.stopPropagation()
    this.setState({ privacyModalOpen: true })
  }

  closePrivacyModal = () => {
    this.setState({ privacyModalOpen: false })
  }

  togglePrivacyModal = (e) => {
    e.preventDefault()
    this.setState({ privacyModalOpen: !this.state.privacyModalOpen });
  }

  renderPrivacyModal() {
    if (!this.state.privacyModalOpen) {
      return null;
    }

    return (
      <Modal className='public-private-modal' isOpen={this.state.privacyModalOpen} toggle={this.closePrivacyModal}>
        <ModalHeader toggle={this.closePrivacyModal} className='dialog-header' >
          <span className='modal-title'>PRIVACY SETTING</span>
        </ModalHeader>
        <ModalBody >
          <div className="row d-flex align-items-center mb-5">
            <div className="col-sm-3">
              <button
                className={"action-button " + (this.props.workflow.public ? "button-blue--fill" : "button-gray") }
                title="Make Public"
                onClick={this.onSetWorkflowPublic}
              >
                  Public
              </button>
            </div>
            <div className="col-sm-9">
              <div className='info-2'>Anyone can access and duplicate the workflow or any of its modules</div>
            </div>
          </div>
          <div className="row d-flex align-items-center">
            <div className="col-sm-3">
              <button
                className={"action-button " + (!this.props.workflow.public ? "button-blue--fill" : "button-gray")}
                title="Make Private"
                onClick={this.onSetWorkflowPrivate}
              >
                  Private
              </button>
            </div>
            <div className="col-sm-9">
              <div className='info-2'>Only you can access and edit the workflow</div>
            </div>
          </div>
        </ModalBody>
        <div className=' modal-footer'>
          <div onClick={this.closePrivacyModal} className='action-button button-gray'>Cancel</div>
        </div>
      </Modal>
    );
  }

  render() {

    var now = this.props.test_now || new Date();


    // only list User attribution if one exists & is not just whitespace
    var user = this.props.workflow.owner_name.trim();
    var attribution = user.length
      ? <li className="attribution">
          <span className="metadata">by {user}</span>
          <span className="separator">-</span>
        </li>
      : null
    var modalLink = (this.props.workflow.read_only)
      ? null
      : <button className="public-private" title="Change privacy" onClick={this.openPrivacyModal}>
          <span className='separator'>-</span>
          <span className='publicPrivate'>{this.props.workflow.public ? 'public' : 'private'}</span>
        </button>

    return (
      <React.Fragment>
        <ul className="metadata-container">
          {attribution}
          <li>
            Updated {timeDifference(this.props.workflow.last_update, now)}
          </li>
          <li>
            {modalLink}
          </li>
        </ul>
        { this.renderPrivacyModal() }
      </React.Fragment>
    );
  }
}
