import React from 'react'
import PropTypes from 'prop-types'
import WfHamburgerMenu from '../WfHamburgerMenu'
import { Trans } from '@lingui/macro'
import { currentLocaleId } from '../i18n/locales'

function getActiveSection () {
  const path = window.location.pathname
  if (path.startsWith('/workflows')) {
    return 'workflows'
  } else if (path.startsWith('/settings')) {
    return 'settings'
  } else {
    return 'lessons'
  }
}

function propsForLink (activeSection, name, href) {
  if (name === activeSection) {
    return { href: null, className: 'active' }
  } else {
    return { href: href, className: 'inactive' }
  }
}

export default class Navbar extends React.Component {
  static propTypes = {
    user: PropTypes.object // null/undefined if logged out
  }

  render () {
    const activeSection = getActiveSection()
    const { user } = this.props

    return (
      <div>
        <nav className='navbar'>
          <div className='logo'>
            <img src={`${window.STATIC_URL}images/logo.svg`} className='logo' />
            <img src={`${window.STATIC_URL}images/logo-text-dark.svg`} className='logo-text' />
          </div>
          <div className='links'>
            <a {...propsForLink(activeSection, 'workflows', '/workflows')}>
              <Trans id='js.Workflows.NavBar.links.workflows' comment='This is used in navigation bar. It should be all-caps for styling reasons.'>WORKFLOWS</Trans>
            </a>
            <a {...propsForLink(activeSection, 'lessons', `/lessons/${currentLocaleId}`)}>
              <Trans id='js.Workflows.NavBar.links.training' comment='This is used in navigation bar. It should be all-caps for styling reasons.'>TRAINING</Trans>
            </a>
            {activeSection === 'settings' ? (
              <a {...propsForLink(activeSection, 'settings', '/settings/billing')}>
                <Trans id='js.Workflows.NavBar.links.settings' comment='This is used in navigation bar. It should be all-caps for styling reasons.'>SETTINGS</Trans>
              </a>
            ) : null /* we only show "Settings" if the user is on it -- it is hidden, [2020-11-19] for now */}
          </div>
          <WfHamburgerMenu user={user} />
        </nav>
      </div>
    )
  }
}
