// Navbar at top of all logged-in pages.
// May have various elements on different pages, including toolbar

import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'
import EditableWorkflowName from './EditableWorkflowName'
import WorkflowMetadata from './WorkflowMetadata'
import PropTypes from 'prop-types'
import { goToUrl } from './utils'


export class WorkflowListNavBar extends React.Component {

  render() {

    return (
      <div>
        <nav className="navbar">
          <div className="navbar-brand d-flex flex-row align-items-center">
            <img src="/static/images/logo.svg" className="logo"/>
            <h1 className="mb-0 mr-auto logo-1"><a href="/workflows">Workbench</a></h1>
          </div>
          <div className='d-flex flex-row align-items-center'>
            <a href="http://cjworkbench.org/index.php/blog/" className='t-white content-2 mr-5'>Learn</a>
            <WfHamburgerMenu />
          </div>
        </nav>
      </div>
    );
  }
}

// Workflow page
export class WorkflowNavBar extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      spinnerVisible: false
    };
    this.handleDuplicate = this.handleDuplicate.bind(this);
  }

  // TODO: follow this pattern for Share button
  handleDuplicate() {
    if ((typeof this.props.user !== 'undefined' && !this.props.user.id)) {
      // user is NOT logged in, so navigate to sign in
      goToUrl('/account/login');
    } else {
      // user IS logged in: start spinner, make duplicate & navigate there
      this.setState({spinnerVisible: true});

      this.props.api.duplicate(this.props.workflow.id)
        .then(json => {
          goToUrl('/workflows/' + json.id);
        })
    }
  }

  render() {

    // checks if there is a logged-in user, true = logged out
    var signOff = ((typeof this.props.user !== 'undefined' && !this.props.user.id))
      ? <a href="http://app.cjworkbench.org/account/login" className='nav-link t-white content-2'>Sign in</a>
      : <WfHamburgerMenu
          wfId={this.props.workflow.id}
          api={this.props.api}
          isReadOnly={this.props.isReadOnly}
          user={this.props.user}
        />

    var duplicate = (this.props.workflow.public)
      ? <div onClick={this.handleDuplicate} className='button-white action-button test-duplicate-button'>
          Duplicate and Edit
        </div>
      : null

    var spinner = (this.state.spinnerVisible)
      ? <div id="spinner-container">
          <div id="spinner-l1">
            <div id="spinner-l2">
              <div id="spinner-l3"></div>
            </div>
          </div>
        </div>
      : null

    return (
      <div>
        {spinner}
        <nav className="navbar-workflows">
          <div className="navbar-brand d-flex flex-row align-items-center">
            <div className='title-metadata-stack'>
              <EditableWorkflowName
                value={this.props.workflow.name}
                wfId={this.props.workflow.id}
                isReadOnly={this.props.workflow.read_only}
                api={this.props.api}
              />
              <WorkflowMetadata
                workflow={this.props.workflow}
                api={this.props.api}
                user={this.props.user}
              />
            </div>
          </div>
          <div className='d-flex flex-row align-items-center'>
            {duplicate}
            <a href="http://cjworkbench.org/index.php/blog/" className='nav-link t-white content-2'>
              Learn
            </a>
            {signOff}
          </div>
        </nav>
      </div>
    );
  }
}

WorkflowNavBar.propTypes = {
  api:        PropTypes.object.isRequired,
  workflow:   PropTypes.object,
  isReadOnly: PropTypes.bool.isRequired,
  user:       PropTypes.object
};
