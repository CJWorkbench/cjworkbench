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
          <h1 className="navbar-brand mb-0 mr-auto title-3">CJ Workbench</h1>
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
          <WfHamburgerMenu workflowId={this.props.workflowId} api={this.props.api} />
        </nav>
      </div>
    );
  }
}

WorkflowNavBar.propTypes = {
  api:              PropTypes.object.isRequired,
  workflowId:       PropTypes.number.isRequired
};


