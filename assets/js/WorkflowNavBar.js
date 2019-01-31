import React from 'react'
import PropTypes from 'prop-types'
import WfHamburgerMenu from './WfHamburgerMenu'
import UndoRedoButtons from './UndoRedoButtons'
import EditableWorkflowName from './EditableWorkflowName'
import WorkflowMetadata from './WorkflowMetadata'
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

  componentWillUnmount = () => {
    this.unmounted = true
  }

  undoRedo (verb) {
    // TODO use reducer for this, with a global "can't tell what's going to
    // change" flag instead of this.state.spinnerVisible.

    // Prevent keyboard shortcuts or mouse double-undoing.
    if (this.state.spinnerVisible) return

    this.setState({ spinnerVisible: true })
    this.props.api[verb](this.props.workflow.id)
      .then(() => {
        if (this.unmounted) return
        this.setState({ spinnerVisible: false })
      })
  }

  undo = () => {
    this.undoRedo('undo')
  }

  redo = () => {
    this.undoRedo('redo')
  }

  handleDuplicate = () => {
    if (!this.props.loggedInUser) {
      // user is NOT logged in, so navigate to sign in
      goToUrl('/account/login')
    } else {
      // user IS logged in: start spinner, make duplicate & navigate there
      this.setState({ spinnerVisible: true })

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
    const { api, isReadOnly, loggedInUser, workflow } = this.props

    // menu only if there is a logged-in user
    let contextMenu
    if (loggedInUser) {
      contextMenu = (
        <WfHamburgerMenu
          workflowId={workflow.id}
          api={api}
          isReadOnly={isReadOnly}
          user={loggedInUser}
        />
      )
    } else {
      contextMenu = (
        <a href="/account/login" className='nav--link'>Sign in</a>
      )
    }

    const spinner = this.state.spinnerVisible ? (
      <div className="spinner-container">
        <div className="spinner-l1">
          <div className="spinner-l2">
            <div className="spinner-l3"></div>
          </div>
        </div>
      </div>
    ) : null

    const shareModal = this.state.isShareModalOpen ? (
      <ShareModal
        api={api}
        logShare={this.logShare}
        onClickClose={this.closeShareModal}
      />
    ) : null

    return (
      <React.Fragment>
        {spinner}
        <nav className='navbar'>
          <div className="navbar-elements">
            <a href='/workflows/' className='logo-navbar'>
              <img className='image' src={`${window.STATIC_URL}images/logo.svg`}/>
            </a>
            <div className='title-metadata-stack'>
              <EditableWorkflowName isReadOnly={isReadOnly} />
              <WorkflowMetadata workflow={this.props.workflow} openShareModal={this.openShareModal} />
            </div>
            <div className='nav-buttons'>
              {isReadOnly ? null : (
                <UndoRedoButtons undo={this.undo} redo={this.redo} />
              )}
              <button name='duplicate' onClick={this.handleDuplicate}>Duplicate</button>
              <button name='share' onClick={this.openShareModal}>Share</button>
              {contextMenu}
            </div>
          </div>
        </nav>
        {shareModal}
      </React.Fragment>
    )
  }
}
