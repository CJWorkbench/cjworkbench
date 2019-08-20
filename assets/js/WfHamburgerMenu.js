// "Hamburger" drop down on workflow and workflows page. Fixed contents.

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from './components/Dropdown'
import ImportModuleFromGitHub from './ImportModuleFromGitHub'
import LocaleSwitcher from './i18n/LocaleSwitcher'

export default class WfHamburgerMenu extends React.Component {
  static propTypes = {
    api: PropTypes.object, // not required: WorkflowListNavBar doesn't allow import from github
    workflowId: PropTypes.number, // not required: WorkflowListNavBar has no workflow
    user: PropTypes.shape({
      id: PropTypes.number.isRequired
    }) // if null/undefined, user is not logged in
  }

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
    const { api, workflowId, user } = this.props
    const loggedIn = !!user

    return (
      <>
        <LocaleSwitcher />
        <UncontrolledDropdown>
          <DropdownToggle title='menu' className='context-button'>
            <i className='icon-more' />
          </DropdownToggle>
          <DropdownMenu>
            {loggedIn && workflowId ? (
              <>
                <DropdownItem href='/workflows/'>My Workflows</DropdownItem>
                <DropdownItem onClick={this.openImportModal}>Import Module</DropdownItem>
              </>
            ) : (
              <DropdownItem href='//workbenchdata.com'>Home</DropdownItem>
            )}
            {loggedIn ? (
              <DropdownItem href='/account/logout'>Log Out</DropdownItem>
            ) : null}
          </DropdownMenu>
        </UncontrolledDropdown>
        {this.state.importModalOpen ? (
          <ImportModuleFromGitHub
            closeModal={this.closeImportModal}
            api={api}
          />
        ) : null}
      </>
    )
  }
}
