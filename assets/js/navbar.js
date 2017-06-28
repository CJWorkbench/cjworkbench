// Navbar at top of all logged-in pages.
// May have various elements on different pages, including toolbar

import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'
import ImportModuleFromGitHub from './ImportModuleFromGitHub'
import PropTypes from 'prop-types'


export class WorkflowListNavBar extends React.Component {

  render() {

    return (
      <div>
        <nav className="navbar">
          <h1 className="navbar-brand mb-0 mr-auto">CJ Workbench</h1>
          <WfHamburgerMenu workflowsPage />
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
          {/*<h3 className="mx-auto">{this.props.workflowTitle}</h3>*/}
          <WfHamburgerMenu />
        </nav>
      </div>
    );
  }
}

WorkflowNavBar.propTypes = {
  addButton:        PropTypes.object,
  workflowTitle:    PropTypes.string,
  importModule:     PropTypes.object,
};


