// "Hamburger" drop down on workflow and workflows page. Fixed contents.

import React from 'react'
import PropTypes from 'prop-types'
import UncontrolledDropdown from 'reactstrap/lib/UncontrolledDropdown'
import DropdownToggle from 'reactstrap/lib/DropdownToggle'
import DropdownMenu from 'reactstrap/lib/DropdownMenu'
import DropdownItem from 'reactstrap/lib/DropdownItem'
import ImportModuleFromGitHub from './ImportModuleFromGitHub'

export default class WfHamburgerMenu extends React.Component {
  constructor (props) {
    super(props)
    this.toggleImportModal = this.toggleImportModal.bind(this)

    this.state = {
      importModalOpen: false
    }
  }

  toggleImportModal () {
    this.setState({ importModalOpen: !this.state.importModalOpen })
  }

  renderImportModal () {
    return (
      <ImportModuleFromGitHub
        closeModal={this.toggleImportModal}
        api={this.props.api}
      />
    )
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
      let importModal = this.state.importModalOpen ? this.renderImportModal() : null

      importModule = (
        <DropdownItem onClick={this.toggleImportModal} className='test-export-button'>
          <span>Import Module</span>
          {importModal}
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
      <UncontrolledDropdown>
        <DropdownToggle title='menu' className='context-button'>
          <i className='context-button--icon icon-more' />
        </DropdownToggle>
        <DropdownMenu right>
          {homeLink}
          {importModule}
          {logInorOut}
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}

// api, isReadOnly not required because they aren't needed (or set) when we're called from WorkflowListNavBar
WfHamburgerMenu.propTypes = {
  api: PropTypes.object,
  workflowId: PropTypes.number,
  isReadOnly: PropTypes.bool,
  user: PropTypes.object
}
