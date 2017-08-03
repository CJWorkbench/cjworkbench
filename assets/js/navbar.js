// Navbar at top of all logged-in pages.
// May have various elements on different pages, including toolbar

import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'
import PropTypes from 'prop-types'


export class WorkflowListNavBar extends React.Component {

  render() {

    return (
      <div>
        <nav className="navbar">
          <div className="navbar-brand">
            <img src="/static/images/logo.png" className="logo"/>
            <h1 className="mb-0 mr-auto title-2"><a href="http://cjworkbench.org">Workbench</a></h1>
          </div>
          <WfHamburgerMenu />
        </nav>
      </div>
    );
  }
}

// Workflow page
export class WorkflowNavBar extends React.Component {

  render() {

    return (
      <div>
        <nav className="navbar">
          <div className="navbar-brand">
            <img src="/static/images/logo.png" className="logo"/>
            <h1 className="mb-0 mr-auto title-2"><a href="http://cjworkbench.org">Workbench</a></h1>
          </div>
          <WfHamburgerMenu workflowId={this.props.workflowId} api={this.props.api} isReadOnly={this.props.isReadOnly} />
        </nav>
      </div>
    );
  }
}

WorkflowNavBar.propTypes = {
  api:              PropTypes.object.isRequired,
  workflowId:       PropTypes.number.isRequired
};
