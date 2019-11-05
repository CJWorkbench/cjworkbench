// "Hamburger" drop down on workflow and workflows page. Fixed contents.

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from './components/Dropdown'
import ImportModuleFromGitHub from './ImportModuleFromGitHub'
import LocaleSwitcher from './i18n/LocaleSwitcher'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export class WfHamburgerMenu extends React.Component {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    api: PropTypes.object, // not required: WorkflowListNavBar doesn't allow import from github
    workflowId: PropTypes.number, // not required: WorkflowListNavBar has no workflow
    user: PropTypes.shape({
      id: PropTypes.number.isRequired
    }) // if null/undefined, user is not logged in
  }

  state = {
    importModalOpen: false
  }

  handleClickOpenImportModal = () => {
    this.setState({ importModalOpen: true })
  }

  closeImportModal = () => {
    this.setState({ importModalOpen: false })
  }

  render () {
    const { api, workflowId, user, i18n } = this.props
    const loggedIn = !!user

    return (
      <>
        <LocaleSwitcher />
        <UncontrolledDropdown>

          <DropdownToggle title={i18n._(t('js.WfHamburgerMenu.toggle.hoverText')`menu`)} className='context-button'>
            <i className='icon-more' />
          </DropdownToggle>

          <DropdownMenu>
            {loggedIn && workflowId ? (
              <>
                <DropdownItem href='/workflows/'><Trans id='js.WfHamburgerMenu.menu.myWorkflows'>My Workflows</Trans></DropdownItem>
                <DropdownItem onClick={this.handleClickOpenImportModal}><Trans id='js.WfHamburgerMenu.menu.importModule'>Import Module</Trans></DropdownItem>
              </>
            ) : (
              <DropdownItem href='//workbenchdata.com'><Trans id='js.WfHamburgerMenu.menu.home'>Home</Trans></DropdownItem>
            )}
            {loggedIn ? (
              <DropdownItem href='/account/logout'><Trans id='js.WfHamburgerMenu.menu.logout'>Log Out</Trans></DropdownItem>
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

export default withI18n()(WfHamburgerMenu)
