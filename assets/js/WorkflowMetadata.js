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

import timediff from 'timediff'



export default class WorkflowMetadata extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      isPublic: props.workflow.public,
      privacyModalOpen: false
    };
    this.setPublic = this.setPublic.bind(this);
    this.togglePrivacyModal = this.togglePrivacyModal.bind(this);
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.workflow === undefined) {
      return false;
    }

    this.setState({
      isPublic: nextProps.workflow.public
    });
  }

  setPublic(isPublic) {
    this.props.api.setWorkflowPublic(this.props.workflow.id, isPublic)
    .then(() => {
      this.setState({isPublic: isPublic});
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
            <div className="col-sm-4">
              <div
                className={"action-button " + (this.state.isPublic ? "button-full-blue" : "button-gray") }
                onClick={() => {this.setPublic(true); this.togglePrivacyModal()}}>
                  Public
              </div>
            </div>
            <div className="col-sm-8">
              <p>Anyone can access and duplicate the workflow or any of its modules</p>
            </div>
          </div>
          <br></br>
          <div className="row">
            <div className="col-sm-4">
              <div
                className={"action-button " + (!this.state.isPublic ? "button-full-blue" : "button-gray")}
                onClick={() => {this.setPublic(false); this.togglePrivacyModal()}}>
                  Private
              </div>
            </div>
            <div className="col-sm-8">
              <p>Only you can access and edit he workflow</p>
            </div>
          </div>
        </ModalBody>
      </Modal>
    );
  }

  // takes 2 date objects, returns a string with time difference (rounded up to largest time unit)
  // should live in ./Utils, but causing errors - needs investigation
  timeDifference(start, end) {
    var diff = timediff(start,end);

    if (diff.years > 0) {
      return "" + diff.years + " years ago";
    }
    else if (diff.days > 0) {
      return "" + diff.days + " days ago";
    }
    else if (diff.hours > 0) {
      return "" + diff.hours + " hours ago";
    }
    else if (diff.minutes > 0) {
      return "" + diff.minutes + " minutes ago";
    }
    else {
      return "just now";
    }
  }

  render() {
    return (
      <div>
        <ul className="list-inline list-workflow-meta">
          <li className="list-inline-item">by <strong>{this.props.workflow.owner_name}</strong></li>
          <li className="list-inline-item">
            updated <strong>{this.timeDifference(this.props.workflow.last_update, new Date())}</strong>
          </li>
          <li className="list-inline-item t-f-blue" onClick={this.togglePrivacyModal}>
            <strong>{this.state.isPublic ? 'public' : 'private'}</strong></li>
        </ul>
        { this.renderPrivacyModal() }
      </div>
    );
  }
}

WorkflowMetadata.propTypes = {
  workflow: PropTypes.object.isRequired,
  api:      PropTypes.object.isRequired,
};