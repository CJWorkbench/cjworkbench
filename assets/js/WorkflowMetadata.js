// WorkflowMetadata: that line below the workflow title
// which shows owner, last modified date, public/private

import React from 'react'
import PropTypes from 'prop-types'
import {
  Button,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter
} from 'reactstrap'
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

  setPublic(isPublic) {
    this.props.api.setWorkflowPublic(this.props.workflow.id, isPublic)
    .then(() => {
      this.setState({isPublic: isPublic});
      // hard reload, to ensure consistency of state with Share button in parent Navbar component
      location.reload();
    })
    .catch((error) => {
      console.log('Request failed', error);
    });
  }

  togglePrivacyModal() {
    this.setState({ privacyModalOpen: !this.state.privacyModalOpen });
  }

  renderPrivacyModal() {
    if (!this.state.privacyModalOpen) {
      return null;
    }

    return (
      <Modal isOpen={this.state.privacyModalOpen} toggle={this.togglePrivacyModal}>
        <ModalHeader toggle={this.togglePrivacyModal} className='dialog-header' >
          <span className='t-d-gray title-4'>Privacy Setting</span>
        </ModalHeader>
        <ModalBody className='dialog-body'>
          <div className="row">
            <div className="col-sm-3">
              <div
                className={"action-button " + (this.state.isPublic ? "button-full-blue" : "button-gray test-button-gray") }
                onClick={() => {this.setPublic(true); this.togglePrivacyModal()}}>
                  Public
              </div>
            </div>
            <div className="col-sm-9">
              <p>Anyone can access and duplicate the workflow or any of its modules</p>
            </div>
          </div>
          <br></br>
          <div className="row d-flex align-items-center">
            <div className="col-sm-3">
              <div
                className={"action-button " + (!this.state.isPublic ? "button-full-blue" : "button-gray test-button-gray")}
                onClick={() => {this.setPublic(false); this.togglePrivacyModal()}}>
                  Private
              </div>
            </div>
            <div className="col-sm-9 mt-2 mb-3">
              <p>Only you can access and edit the workflow</p>
            </div>
          </div>
        </ModalBody>
      </Modal>
    );
  }

  render() {

    var now = this.props.test_now || new Date();

    // only list User attribution if one exists & is not just whitespace
    var user = (this.props.user && this.props.user.display_name)
      ? this.props.user.display_name
      : null
    var attribution = (user && user.replace(/\s/g, '').length)
      ? <li className="list-inline-item content-3">by {user}</li>
      : null
    var modalLink = (this.props.workflow.read_only)
      ? null
      : <li className="list-inline-item test-button content-3 " onClick={this.togglePrivacyModal}>
          <u>{this.state.isPublic ? 'public' : 'private'}</u>
        </li>

    var textColor = this.props.inWorkflowList? 't-f-blue': 't-white';

    return (
      <div className=''>
        <ul className={"list-inline workflow-meta content-3 "+textColor}>
           {attribution}
          <li className="list-inline-item content-3 ">
            Updated {timeDifference(this.props.workflow.last_update, now)}
          </li>
          {modalLink}
        </ul>
        { this.renderPrivacyModal() }
      </div>
    );
  }
}

WorkflowMetadata.propTypes = {
  workflow:   PropTypes.object.isRequired,
  api:        PropTypes.object.isRequired,
  isPublic:   PropTypes.bool.isRequired,
  user:       PropTypes.object,
  inWorkflowList: PropTypes.bool, //change styling for use inside WF list
  test_now:   PropTypes.object  // optional injection for testing

};
