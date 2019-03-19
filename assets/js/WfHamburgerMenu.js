// "Hamburger" drop down on workflow and workflows page. Fixed contents.

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from './components/Dropdown'
import ImportModuleFromGitHub from './ImportModuleFromGitHub'

export default class WfHamburgerMenu extends React.Component {
  state = {
    importModalOpen: false
  }

  openImportModal = () => {
    this.setState({ importModalOpen: true })
  }

  closeImportModal = () => {
    this.setState({ importModalOpen: false })
  }

  render () {
    let homeLink = null
    let undoRedo = null
    let logInorOut = null
    let importModule = null

    let loggedIn = typeof this.props.user !== 'undefined' && this.props.user.id

    if (this.props.workflowId) { // on Wf page
      if (loggedIn) {
        homeLink = (
          <DropdownItem href='/workflows'>
            <span>My Workflows</span>
          </DropdownItem>
        )
      } else {
        homeLink = (
          <DropdownItem href='https://workbenchdata.com'>
            <span>Home</span>
          </DropdownItem>
        )
      }
    }

    // can import if logged in
    if (loggedIn) {
      importModule = (
        <DropdownItem onClick={this.openImportModal}>
          <span>Import Module</span>
        </DropdownItem>
      )
    }

    // either log in or out
    if (loggedIn) {
      logInorOut = (
        <DropdownItem href='/account/logout'>
          <span>Log Out</span>
        </DropdownItem>
      )
    } else {
      logInorOut = (
        <DropdownItem href='/account/logout'>
          <span>Log out</span>
        </DropdownItem>
      )
    }

    return (
      <React.Fragment>
        <UncontrolledDropdown>
          <DropdownToggle title='menu' className='context-button'>
            <i className='context-button--icon icon-more' />
          </DropdownToggle>
          <DropdownMenu positionFixed right>
            {homeLink}
            {importModule}
            {logInorOut}
          </DropdownMenu>
        </UncontrolledDropdown>
        {this.state.importModalOpen ? (
          <ImportModuleFromGitHub
            closeModal={this.closeImportModal}
            api={this.props.api}
          />
        ) : null}
      </React.Fragment>
    )
  }
}

// api, isReadOnly not required because they aren't needed (or set) when we're called from WorkflowListNavBar
WfHamburgerMenu.propTypes = {
  api: PropTypes.object,
  workflowId: PropTypes.number,
  isReadOnly: PropTypes.bool,
  user: PropTypes.shape({
    id: PropTypes.number.isRequire,
  }) // if null/undefined, user is not logged in
}
