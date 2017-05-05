// Navbar at top of all logged-in pages.
// May have various elements on different pages, including toolbar

import React from 'react';
import WorkflowHamburgerMenu from './WorkflowHamburgerMenu'

export class NavBar extends React.Component {

  render() {

    // fixed navbar (not visible) to space content below floating navbar, then real navbar
    return (
      <div>
        <nav className="navbar navbar-toggleable-md mb-3">
          <h1 className="navbar-brand mb-0">CJ Workbench</h1>
        </nav>

        <nav className="navbar fixed-top navbar-toggleable-md navbar-light bg-faded border-bottom-1">
          <h1 className="navbar-brand mb-0 mr-auto">CJ Workbench</h1>
          <WorkflowHamburgerMenu workflowsPage />
        </nav>
      </div>
    );
  }
}

export class WorkflowNavBar extends React.Component {

  render() {

    // fixed navbar (not visible) to space content below floating navbar, then real navbar
    return (
      <div>
        <nav className="navbar navbar-toggleable-md mb-3">
          <h3>spacing text</h3>
        </nav>

        <nav className="navbar fixed-top navbar-toggleable-md navbar-light bg-faded border-bottom-1">
          {this.props.addButton}
          <h3 className="mx-auto">{this.props.workflowTitle}</h3>
          <WorkflowHamburgerMenu />
        </nav>
      </div>
    );
  }
}

WorkflowNavBar.propTypes = {
  addButton:        React.PropTypes.object,
  workflowTitle:    React.PropTypes.string,
};


