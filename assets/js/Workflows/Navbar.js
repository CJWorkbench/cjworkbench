import React from 'react'
import PropTypes from 'prop-types'
import WfHamburgerMenu from '../WfHamburgerMenu'
import { Trans } from '@lingui/macro'

function getActiveSection () {
  return window.location.pathname.startsWith('/workflows') ? 'workflows' : 'lessons'
}

function propsForLink (activeSection, name) {
  if (name === activeSection) {
    return { href: null, className: 'active' }
  } else {
    return { href: `/${name}`, className: 'inactive' }
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
            <a {...propsForLink(activeSection, 'workflows')}>
              <Trans id='js.Workflows.NavBar.links.workflows' description='This is used in navigation bar. It should be all-caps for styling reasons.'>WORKFLOWS</Trans>
            </a>
            <a {...propsForLink(activeSection, 'lessons')}>
              <Trans id='js.Workflows.NavBar.links.training' description='This is used in navigation bar. It should be all-caps for styling reasons.'>TRAINING</Trans>
            </a>
          </div>
          <WfHamburgerMenu user={user} />
        </nav>
      </div>
    )
  }
}
