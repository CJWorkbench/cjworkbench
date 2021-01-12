import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownDivider, DropdownToggle, DropdownMenu, DropdownItem } from './components/Dropdown'
import ImportModuleFromGitHub from './ImportModuleFromGitHub'
import LocaleSwitcher from './i18n/LocaleSwitcher'
import { csrfToken } from './utils'
import { Trans, t } from '@lingui/macro'

const DisplayNoneStyle = { display: 'none' }

/**
 * "Hamburger" drop down on workflow and workflows page.
 */
export default function WfHamburgerMenu (props) {
  const { api = null, workflowId = null, user = null } = props

  const [isImportModalOpen, setImportModalOpen] = React.useState(false)
  const [isLocaleSwitcherOpen, setLocaleSwitcherOpen] = React.useState(false)
  const logoutFormRef = React.useRef(null)

  const handleClickOpenImportModal = React.useCallback(
    () => setImportModalOpen(true),
    [setImportModalOpen]
  )
  const handleCloseImportModal = React.useCallback(
    () => setImportModalOpen(false),
    [setImportModalOpen]
  )
  const handleClickOpenLocaleSwitcher = React.useCallback(
    () => setLocaleSwitcherOpen(true),
    [setLocaleSwitcherOpen]
  )
  const handleCloseLocaleSwitcher = React.useCallback(
    () => setLocaleSwitcherOpen(false),
    [setLocaleSwitcherOpen]
  )
  const handleClickLogOut = React.useCallback(
    () => {
      const logoutForm = logoutFormRef.current
      if (logoutForm) {
        logoutForm.submit()
      }
    },
    [logoutFormRef]
  )

  const loggedIn = !!user

  return (
    <>
      <UncontrolledDropdown>

        <DropdownToggle
          title={t({ id: 'js.WfHamburgerMenu.toggle.hoverText', message: 'menu' })}
          className='context-button'
        >
          <i className='icon-more' />
        </DropdownToggle>

        <DropdownMenu>
          <DropdownItem onClick={handleClickOpenLocaleSwitcher}>
            <i className='icon icon-language' /><Trans id='js.WfHamburgerMenu.menu.language'>Language</Trans>
          </DropdownItem>
          <DropdownDivider />
          {loggedIn && workflowId ? (
            <>
              <DropdownItem href='/workflows/'>
                <Trans id='js.WfHamburgerMenu.menu.myWorkflows'>My Workflows</Trans>
              </DropdownItem>
              <DropdownItem onClick={handleClickOpenImportModal}>
                <Trans id='js.WfHamburgerMenu.menu.importModule'>Import Module</Trans>
              </DropdownItem>
            </>
          ) : (
            <DropdownItem href='//workbenchdata.com'>
              <Trans id='js.WfHamburgerMenu.menu.home'>Home</Trans>
            </DropdownItem>
          )}
          {loggedIn ? (
            <DropdownItem onClick={handleClickLogOut}>
              <Trans id='js.WfHamburgerMenu.menu.logout'>Log Out</Trans>
            </DropdownItem>
          ) : null}
        </DropdownMenu>
      </UncontrolledDropdown>
      {loggedIn ? (
        <form ref={logoutFormRef} style={DisplayNoneStyle} method='post' action='/account/logout/'>
          <input type='hidden' name='csrfmiddlewaretoken' value={csrfToken} />
          <input type='submit' />
        </form>
      ) : null}
      {isImportModalOpen ? (
        <ImportModuleFromGitHub
          closeModal={handleCloseImportModal}
          api={api}
        />
      ) : null}
      {isLocaleSwitcherOpen ? (
        <LocaleSwitcher
          closeModal={handleCloseLocaleSwitcher}
        />
      ) : null}
    </>
  )
}
WfHamburgerMenu.propTypes = {
  api: PropTypes.object, // not required: WorkflowListNavBar doesn't allow import from github
  workflowId: PropTypes.number, // not required: WorkflowListNavBar has no workflow
  user: PropTypes.object // if null/undefined, user is not logged in
}
