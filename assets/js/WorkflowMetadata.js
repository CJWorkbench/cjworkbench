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


export default class WorkflowMetadata extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      isPublic: this.props.isPublic,
      privacyModalOpen: false
    };
    this.setPublic = this.setPublic.bind(this);
    this.togglePrivacyModal = this.togglePrivacyModal.bind(this);
  }

  // Listens for changes from parent
  componentWillReceiveProps(nextProps) {
    if (nextProps.workflow === undefined) {
      return false;
    }

    this.setState({
      isPublic: nextProps.isPublic
    });
  }

  reloadPageToEnsureConsistencyBecauseNavbarDoesntListenToState() {
    // hard reload, to ensure consistency of state with Share button in parent Navbar component
    location.reload();
  }

  setPublic(isPublic) {
    // FIXME use redux
    this.props.api.setWorkflowPublic(this.props.workflow.id, isPublic)
      .then(() => {
        this.setState({isPublic: isPublic});
        this.reloadPageToEnsureConsistencyBecauseNavbarDoesntListenToState()
      })
      .catch((error) => {
        console.log('Request failed', error);
      });
  }

  togglePrivacyModal(e) {
    e.preventDefault()
    this.setState({ privacyModalOpen: !this.state.privacyModalOpen });
  }

  renderPrivacyModal() {
    if (!this.state.privacyModalOpen) {
      return null;
    }

    return (
      <Modal isOpen={this.state.privacyModalOpen} toggle={this.togglePrivacyModal}>
        <ModalHeader toggle={this.togglePrivacyModal} className='dialog-header' >
          <span className='t-d-gray title-4'>PRIVACY SETTING</span>
        </ModalHeader>
        <ModalBody >
          <div className="row d-flex align-items-center mb-5">
            <div className="col-sm-3">
              <div
                className={"action-button " + (this.state.isPublic ? "button-blue--fill" : "button-gray test-button-gray") }
                onClick={(e) => {this.setPublic(true); this.togglePrivacyModal(e)}}>
                  Public
              </div>
            </div>
            <div className="col-sm-9">
              <div className='info-2'>Anyone can access and duplicate the workflow or any of its modules</div>
            </div>
          </div>
          <div className="row d-flex align-items-center">
            <div className="col-sm-3">
              <div
                className={"action-button " + (!this.state.isPublic ? "button-blue--fill" : "button-gray test-button-gray")}
                onClick={(e) => {this.setPublic(false); this.togglePrivacyModal(e)}}>
                  Private
              </div>
            </div>
            <div className="col-sm-9">
              <div className='info-2'>Only you can access and edit the workflow</div>
            </div>
          </div>
        </ModalBody>
        <div className=' modal-footer'>
          <div onClick={this.togglePrivacyModal} className='action-button button-gray'>Cancel</div>
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
      : <div className="metadata test-button" onClick={this.togglePrivacyModal}>
          <span className='separator'>-</span>
          <span className='publicPrivate'>{this.state.isPublic ? 'public' : 'private'}</span>
        </div>

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

WorkflowMetadata.propTypes = {
  workflow:   PropTypes.object.isRequired,
  api:        PropTypes.object.isRequired,
  isPublic:   PropTypes.bool.isRequired,
  inWorkflowList: PropTypes.bool, //change styling for use inside WF list
  test_now:   PropTypes.object  // optional injection for testing, avoid time zone issues for Last Update time
};
