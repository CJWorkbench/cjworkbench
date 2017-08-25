// Navbar at top of all logged-in pages.
// May have various elements on different pages, including toolbar

import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'
import EditableWorkflowName from './EditableWorkflowName'
import WorkflowMetadata from './WorkflowMetadata'
import PropTypes from 'prop-types'


export class WorkflowListNavBar extends React.Component {

  render() {

    return (
      <div>
        <nav className="navbar">
          <div className="navbar-brand d-flex flex-row align-items-center">
            <img src="/static/images/logo.png" className="logo"/>
            <h1 className="mb-0 mr-auto title-2"><a href="/workflows">Workbench</a></h1>
          </div>
          <div className='d-flex flex-row align-items-center'>
            <a href="http://cjworkbench.org/index.php/blog/" className='t-white content-2 mr-5'>Help</a>
            <WfHamburgerMenu />
          </div>
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
          <div className="navbar-brand d-flex flex-row align-items-center">
            <img src="/static/images/logo.png" className="logo"/>
            <div className='editable-title-field ml-3'>
              <EditableWorkflowName
                value={this.props.workflow.name}
                wfId={this.props.workflow.id}
                isReadOnly={this.props.workflow.read_only}
                api={this.props.api}
                editClass='title-workflow t-white'
              />
              <WorkflowMetadata 
                workflow={this.props.workflow} 
                api={this.props.api}
                user={this.props.user}
              />
            </div>
          </div>
          <div className='d-flex flex-row align-items-center'>
            <a href="http://cjworkbench.org/index.php/blog/" className='t-white content-2 mr-5'>Learn</a>
            <WfHamburgerMenu 
              wfId={this.props.workflow.id} 
              api={this.props.api} 
              isReadOnly={this.props.isReadOnly} 
              user={this.props.user} 
            />
          </div>
        </nav>
      </div>
    );
  }
}

WorkflowNavBar.propTypes = {
  api:        PropTypes.object.isRequired,
  workflow:   PropTypes.object.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  user:       PropTypes.object.isRequired
};
