import React from 'react'
import PropTypes from 'prop-types'
import WfHamburgerMenu from '../WfHamburgerMenu'
import { Trans,t } from '@lingui/macro'
import { withI18n,I18n } from '@lingui/react'

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

export class Navbar extends React.Component {
  static propTypes =
   { i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    user: PropTypes.shape({ id: PropTypes.number.isRequired }) // null/undefined if logged out
  }

  render () {
    const activeSection = getActiveSection()
    const { user, i18n } = this.props

    return (
      <div>
        <nav className='navbar'>
          <div className='logo'>
            <img src={`${window.STATIC_URL}images/logo.svg`} className='logo' />
            <img src={`${window.STATIC_URL}images/logo-text-dark.svg`} className='logo-text' />
          </div>
          <div className='links'>
            <a {...propsForLink(activeSection, 'workflows')}>
              <Trans id='workflows.navbar.workflows' description={this.props.i18n._(t('workflow.descriptionworflow')`This is used in navigation bar. It should be all-caps for styling reasons.`)}>WORKFLOWS</Trans>
            </a>
            <a {...propsForLink(activeSection, 'lessons')}>
              <Trans id='workflows.navbar.training' description={this.props.i18n._(t('workflow.descriptionworflow')`This is used in navigation bar. It should be all-caps for styling reasons.`)}>TRAINING</Trans>
            </a>
          </div>
          <WfHamburgerMenu user={user} />
        </nav>
      </div>
    )
  }
}

export default withI18n()(Navbar);
