import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'

export default class WorkflowListNavBar extends React.Component {
  render() {
    return (
      <div>
        <nav className="navbar">
          <div className="d-flex align-items-center">
            <img src="/static/images/logo.svg" className="logo"/>
            <div className="logo-1">Workbench</div>
          </div>
          <WfHamburgerMenu />
        </nav>
      </div>
    )
  }
}
