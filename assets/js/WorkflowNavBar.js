import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'
import EditableWorkflowName from './EditableWorkflowName'
import WorkflowMetadata from './WorkflowMetadata'
import PropTypes from 'prop-types'
import {goToUrl, logUserEvent} from './utils'
import Modal from 'reactstrap/lib/Modal'
import ModalHeader from 'reactstrap/lib/ModalHeader'
import ModalBody from 'reactstrap/lib/ModalBody'
import ModalFooter from 'reactstrap/lib/ModalFooter'
import Form from 'reactstrap/lib/Form'
import FormGroup from 'reactstrap/lib/FormGroup'
import Label from 'reactstrap/lib/Label'
import Input from 'reactstrap/lib/Input'
import CopyToClipboard from 'react-copy-to-clipboard';
import { setWorkflowPublicAction } from './workflow-reducer'
import { connect } from 'react-redux'

// Workflow page
export class WorkflowNavBar extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    onChangeIsPublic: PropTypes.func.isRequired, // func(workflowId, isPublic) => undefined
    workflow: PropTypes.object.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    loggedInUser: PropTypes.object // undefined if no user logged in
  };

  constructor(props) {
    super(props);
    this.state = {
      spinnerVisible: false,
      modalsOpen: false,
      linkCopied: false,
    };
    this.handleDuplicate = this.handleDuplicate.bind(this);
    this.renderModals = this.renderModals.bind(this);
    this.toggleModals = this.toggleModals.bind(this);
    this.onLinkCopy = this.onLinkCopy.bind(this);
    this.onLinkLeave = this.onLinkLeave.bind(this);
  }

  handleDuplicate() {
    if (!this.props.loggedInUser) {
      // user is NOT logged in, so navigate to sign in
      goToUrl('/account/login');
    } else {
      // user IS logged in: start spinner, make duplicate & navigate there
      this.setState({spinnerVisible: true});

      this.props.api.duplicateWorkflow(this.props.workflow.id)
        .then(json => {
          goToUrl('/workflows/' + json.id);
        })
    }
  }

  setPublic = () => {
    this.props.onChangeIsPublic(this.props.workflow.id, true)
  }

  // this does not provide the correct link string yet
  linkString(id) {
    var path = "/workflows/" + id;
    // allowing an out for testing (there is no window.location.href during test)
    if (window.location.href == 'about:blank') {
      return path;
    } else {
      var url = new URL(path, window.location.href).href;
      return url;
    }
  }

  onLinkCopy() {
    this.setState({linkCopied: true});
    this.logShare('URL copied')
  }

  onLinkLeave() {
    this.setState({linkCopied: false});
  }

  logShare(type) {
    logUserEvent('Share workflow ' + type);
  }

  onClickFacebook = () => {
    this.logShare('Facebook')
  }

  onClickTwitter = () => {
    this.logShare('Twitter')
  }

  renderCopyLink() {
    var linkString = this.linkString(this.props.workflow.id);

    if (this.state.linkCopied) {
      return (
        <div className='clipboard copied' >Link copied to clipboard</div>
      );
    } else {
      return (
        <CopyToClipboard text={linkString} onCopy={this.onLinkCopy} className='clipboard'>
          <div>COPY TO CLIPBOARD</div>
        </CopyToClipboard>
      );
    }
  }

  toggleModals() {
    this.setState({ modalsOpen: !this.state.modalsOpen });
  }

  renderModals() {
    const linkString = this.linkString(this.props.workflow.id)
    const facebookUrl = `https://www.facebook.com/sharer.php?u=${encodeURIComponent(linkString)}`
    const twitterUrl = `https://www.twitter.com/share?url=${encodeURIComponent(linkString)}&text=${encodeURIComponent('Check out this chart I made using @cjworkbench:')}`
    const copyLink = this.renderCopyLink()

    var setPublicModal =
      <Modal isOpen={this.state.modalsOpen} toggle={this.toggleModals} className='setpublic-modal'>
        <ModalHeader toggle={this.toggleModals} className='dialog-header modal-header d-flex align-items-center' >
          <div className='modal-title'>SHARE THIS WORKFLOW</div>
        </ModalHeader>
        <ModalBody >
          <div className='title-3 mb-3'>This workflow is currently private</div>
          <div className='info-2 t-d-gray'>Set this workflow to Public in order to share it? Anyone with the URL will be able to access and duplicate it.</div>
        </ModalBody>
        <div className="modal-footer ">
          <button onClick={this.toggleModals} className='button-gray action-button mr-4'>Cancel</button>
          <button title="Make Public" onClick={this.setPublic} className='button-blue action-button'>Set Public</button>
        </div>
      </Modal>

    // TODO: log Twitter shares. Probably need a different component with an "onshare" handler.

    var shareModal =
      <Modal isOpen={this.state.modalsOpen} toggle={this.toggleModals} className='share-modal'>
        <ModalHeader toggle={this.toggleModals} className='dialog-header modal-header d-flex align-items-center' >
          <div className='modal-title'>SHARE THIS WORKFLOW</div>
        </ModalHeader>
        <ModalBody >
          <FormGroup>
            <div className='d-flex align-items-center justify-content-between flex-row'>
              <Label className='dl-file'>PUBLIC URL</Label>
              {copyLink}
            </div>
            <div className='mb-3'>
              <Input type='url' name='url' className='url-link' value={linkString} readOnly/>
            </div>
          </FormGroup>

          <div className='share-links'>
            <a href={twitterUrl} onClick={this.onClickTwitter} className='twitter-share' target='_blank'>
              <i className='icon-twitter' />
              Share
            </a>

            <a href={facebookUrl} onClick={this.onClickFacebook} className='facebook-share' target='_blank'>
              <i className='icon-facebook' />
              Share
            </a>
          </div>
        </ModalBody>

      </Modal>

    if (!this.state.modalsOpen) {
      return null;
    } else if (this.props.workflow.public) {
      return shareModal;
    } else {
      return setPublicModal;
    }
  }

  render() {

    // menu only if there is a logged-in user
    var contextMenu;
    if (this.props.loggedInUser) {
      contextMenu = <WfHamburgerMenu
          workflowId={this.props.workflow.id}
          api={this.props.api}
          isReadOnly={this.props.isReadOnly}
          user={this.props.loggedInUser}
      />
    } else {
      contextMenu = <a href="/account/login" className='nav--link'>Sign in</a>
    }

    var duplicate = <button name='duplicate' onClick={this.handleDuplicate} className='button-white--fill action-button'>
                      Duplicate
                    </button>

    var share = <button name='share' onClick={this.toggleModals} className='button-white action-button'>
                  Share
                </button>

    var modals = this.renderModals();

    var spinner = this.state.spinnerVisible ? (
      <div id="spinner-container">
        <div id="spinner-l1">
          <div id="spinner-l2">
            <div id="spinner-l3"></div>
          </div>
        </div>
      </div>
    ) : null

    return (
      <React.Fragment>
        {spinner}
        <nav className="navbar">
          <a href="/workflows/" className="logo-navbar">
            <img className="image" src={`${window.STATIC_URL}images/logo.svg`}/>
          </a>
          <div className='title-metadata-stack'>
            <EditableWorkflowName
              value={this.props.workflow.name}
              workflowId={this.props.workflow.id}
              isReadOnly={this.props.workflow.read_only}
              api={this.props.api}
            />
            <WorkflowMetadata
              workflow={this.props.workflow}
              onChangeIsPublic={this.props.onChangeIsPublic}
            />
          </div>
          <div className='d-flex flex-row align-items-center'>
            {duplicate}
            {share}
            {modals}
            {contextMenu}
          </div>
        </nav>
      </React.Fragment>
    );
  }
}

function mapStateToProps () {
  return {}
}

function mapDispatchToProps (dispatch) {
  return {
    onChangeIsPublic: (workflowId, isPublic) => {
      dispatch(setWorkflowPublicAction(workflowId, isPublic))
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(WorkflowNavBar)
