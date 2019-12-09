import React from 'react'
import PropTypes from 'prop-types'
import WfHamburgerMenu from '../WfHamburgerMenu'
import { Trans } from '@lingui/macro'
import { currentLocale } from '../i18n/locales'


function getActiveSection () {
  return window.location.pathname.startsWith('/workflows') ? 'workflows' : 'lessons'
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
    user: PropTypes.shape({ id: PropTypes.number.isRequired }) // null/undefined if logged out
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
              <Trans id='js.Workflows.NavBar.links.workflows' description='This is used in navigation bar. It should be all-caps for styling reasons.'>WORKFLOWS</Trans>
            </a>
            <a {...propsForLink(activeSection, 'lessons', `/lessons/${currentLocale}`)}>
              <Trans id='js.Workflows.NavBar.links.training' description='This is used in navigation bar. It should be all-caps for styling reasons.'>TRAINING</Trans>
            </a>
          </div>
          <WfHamburgerMenu user={user} />
        </nav>
      </div>
    )
  }
}
