import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'

export default class WorkflowListNavBar extends React.Component {
  render() {
    // For now, we're hiding Lessons; so there are no links on the page. Only
    // show the links when we're on the /lessons/ page.
    const hideLinksBecauseFeatureIsNotFinished = window.location.href.indexOf('/lessons/') === -1

    const activeLink = window.location.href.indexOf('/lessons') === -1 ? 'workflows' : 'lessons'
    const propsForLink = (name) => {
      const activeProps = { href: null, className: 'active' }
      const inactiveProps = { className: 'inactive' }
      return activeLink === name ? activeProps : inactiveProps
    }
    const links = (
      <div className="links">
        <a href="/workflows/" {...propsForLink('workflows')} className="WF-toggle--link">
          <div>WORKFLOWS</div>
          <div className='WF-link--under'></div>
        </a>
        <a href="/lessons/" {...propsForLink('lessons')} className="LS-toggle--link">
          <div>TRAINING</div>
          <div className='LS-link--under'></div>
        </a>
      </div>
    )

    return (
      <div>
        <nav className="navbar">
          <div className="d-flex align-items-center">
            <img src="/static/images/logo.svg" className="logo"/>
            <div className="logo-1">Workbench</div>
          </div>
          {links}
          <WfHamburgerMenu />
        </nav>
      </div>
    )
  }
}
