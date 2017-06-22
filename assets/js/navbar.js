// Navbar at top of all logged-in pages.
// May have various elements on different pages, including toolbar

import React from 'react';
import WorkflowHamburgerMenu from './WorkflowHamburgerMenu'
import ImportModuleFromGitHub from './ImportModuleFromGitHub'

export class WorkflowListNavBar extends React.Component {

  render() {

    return (
      <div>
        <nav className="navbar">
          <h1 className="navbar-brand mb-0 mr-auto">CJ Workbench</h1>
          <WorkflowHamburgerMenu workflowsPage />
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
          {this.props.addButton}
          <ImportModuleFromGitHub />
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
  importModule:      React.PropTypes.object,
};


