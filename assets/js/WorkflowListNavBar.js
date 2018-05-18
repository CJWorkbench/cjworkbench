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
        <div className="WF-toggle--link">
          <a href="/workflows/" {...propsForLink('workflows')}>WORKFLOWS</a>
          <div className='WF-link--under'></div>
        </div>
        <div className="LS-toggle--link">
          <a href="/lessons/" {...propsForLink('lessons')}>LESSONS</a>
          <div className='LS-link--under'></div>
        </div>
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
