import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'
import EditableWorkflowName from './EditableWorkflowName'
import WorkflowMetadata from './WorkflowMetadata'
import PropTypes from 'prop-types'
import { goToUrl, logUserEvent } from './utils'
import ShareModal from './ShareModal'

export default class WorkflowNavBar extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    workflow: PropTypes.object.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    loggedInUser: PropTypes.object // undefined if no user logged in
  }

  state = {
    spinnerVisible: false,
    isShareModalOpen: false
  }

  handleDuplicate = () => {
    if (!this.props.loggedInUser) {
      // user is NOT logged in, so navigate to sign in
      goToUrl('/account/login')
    } else {
      // user IS logged in: start spinner, make duplicate & navigate there
      this.setState({spinnerVisible: true})

      this.props.api.duplicateWorkflow(this.props.workflow.id)
        .then(json => {
          goToUrl('/workflows/' + json.id)
        })
    }
  }

  closeShareModal = () => {
    this.setState({ isShareModalOpen: false })
  }

  openShareModal = () => {
    this.setState({ isShareModalOpen: true })
  }

  logShare = (type) => {
    logUserEvent('Share workflow ' + type)
  }

  render() {
    // menu only if there is a logged-in user
    let contextMenu
    if (this.props.loggedInUser) {
      contextMenu = (
        <WfHamburgerMenu
          workflowId={this.props.workflow.id}
          api={this.props.api}
          isReadOnly={this.props.isReadOnly}
          user={this.props.loggedInUser}
        />
      )
    } else {
      contextMenu = (
        <a href="/account/login" className='nav--link'>Sign in</a>
      )
    }

    const duplicate = (
      <button name='duplicate' onClick={this.handleDuplicate} className='button-white--fill action-button'>
        Duplicate
      </button>
    )

    const share = (
      <button name='share' onClick={this.openShareModal} className='button-white action-button'>
        Share
      </button>
    )

    const spinner = this.state.spinnerVisible ? (
      <div id="spinner-container">
        <div id="spinner-l1">
          <div id="spinner-l2">
            <div id="spinner-l3"></div>
          </div>
        </div>
      </div>
    ) : null

    const shareModal = this.state.isShareModalOpen ? (
      <ShareModal
        logShare={this.logShare}
        onClickClose={this.closeShareModal}
      />
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
            <WorkflowMetadata workflow={this.props.workflow} openShareModal={this.openShareModal} />
          </div>
          <div className='d-flex flex-row align-items-center'>
            {duplicate}
            {share}
            {contextMenu}
          </div>
        </nav>
        {shareModal}
      </React.Fragment>
    )
  }
}
