// "Hamburger" drop down on workflow and workflows page. Fixed contents.

import React from 'react'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap'
import PropTypes from 'prop-types'
import ImportModuleFromGitHub from './ImportModuleFromGitHub';

export default class WfHamburgerMenu extends React.Component {

  constructor(props) {
    super(props);
    this.toggleImportModal = this.toggleImportModal.bind(this);

    this.state = {
      importModalOpen: false,
    };
  }

  toggleImportModal() {
    this.setState({ importModalOpen: !this.state.importModalOpen });
  }

  renderImportModal() {
    return (
      <ImportModuleFromGitHub
        closeModal={this.toggleImportModal}
        api={this.props.api}
      />
    )
  }

  render() {
    let homeLink=null;
    let undoRedo=null;
    let logInorOut=null;
    let importModule=null;

    let loggedIn = typeof this.props.user !== 'undefined' && this.props.user.id;

    if (this.props.workflowId != undefined) {  // on Wf page
      if (loggedIn) {
        homeLink = (
          <DropdownItem href="/workflows">
            <span>My Workflows</span>
          </DropdownItem>
        );
      } else {
        homeLink = (
          <DropdownItem href="https://workbenchdata.com">
            <span>Home</span>
          </DropdownItem>
        );
      }
    }

    // If we can edit the workflow we have undo and redo items
    if (this.props.workflowId != undefined && !this.props.isReadOnly) {
      undoRedo = (
        <React.Fragment>
          <DropdownItem divider/>
          <DropdownItem onClick={ () => { this.props.api.undo(this.props.workflowId)} }>
            <span>Undo</span>
          </DropdownItem>
          <DropdownItem onClick={ () => { this.props.api.redo(this.props.workflowId)} }>
            <span>Redo</span>
          </DropdownItem>
          <DropdownItem divider/>
        </React.Fragment>
      );
    }

    // can import if logged in
    if (loggedIn) {
      let importModal = this.state.importModalOpen ? this.renderImportModal() : null;

      importModule = (
        <DropdownItem onClick={this.toggleImportModal} className='test-export-button'>
          <span>Import Module</span>
          {importModal}
        </DropdownItem>
      )
    }

    // either log in or out
    if (loggedIn) {
      logInorOut = (
        <DropdownItem href="/account/logout">
           <span>Log Out</span>
        </DropdownItem>
      )
    } else {
      logInorOut =
        <DropdownItem href="/account/logout">
          <span>Log out</span>
        </DropdownItem>
    }

    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <div className='context-button--icon icon-more'></div>
        </DropdownToggle>
        <DropdownMenu right>
          {homeLink}
          {undoRedo}
          {importModule}
          {logInorOut}
        </DropdownMenu>
      </UncontrolledDropdown>
    );
  }
}

// api, isReadOnly not required because they aren't needed (or set) when we're called from WorkflowListNavBar
WfHamburgerMenu.propTypes = {
  api:        PropTypes.object,
  workflowId: PropTypes.number,
  isReadOnly: PropTypes.bool,
  user:       PropTypes.object
};
