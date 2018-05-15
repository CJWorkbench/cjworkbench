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
        moduleAdded={() => {}}
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
        homeLink =
          <DropdownItem
            key={1}
            tag="a"
            href="/workflows"
            className='dropdown-menu--item'
          >
            <span className='content-3 ml-3'>My Workflows</span>
          </DropdownItem>;
      } else {
        homeLink =
          <DropdownItem
            key={1}
            tag="a"
            href="https://workbenchdata.com"
            className='dropdown-menu--item'
          >
            <span className='content-3 ml-3'>Home</span>
          </DropdownItem>
      }

    }

    // If we can edit the workflow we have undo and redo items
    if (this.props.workflowId != undefined && !this.props.isReadOnly) {

      undoRedo =
        <div>
          <DropdownItem divider key={100} />
          <DropdownItem
            key={2}
            onClick={ () => { this.props.api.undo(this.props.workflowId)} }
            className='dropdown-menu--item'
          >
            <span className='content-3 ml-3'>Undo</span>
          </DropdownItem>
          <DropdownItem
            key={3}
            onClick={ () => { this.props.api.redo(this.props.workflowId)} }
            className='dropdown-menu--item'
          >
            <span className='content-3 ml-3'>Redo</span>
          </DropdownItem>
          <DropdownItem divider key={200} />
        </div>;
    }

    // can import if logged in
    if (loggedIn) {
      let importModal = this.state.importModalOpen ? this.renderImportModal() : null;

      importModule =
        <div>
          <DropdownItem divider key={100} />
          <DropdownItem key={4}
            onClick={this.toggleImportModal} className='dropdown-menu--item mb-1 test-export-button'>
            <span className='content-3 ml-3'>Import Module</span>
            {importModal}
          </DropdownItem>
        </div>
    }

    // either log in or out
    if (loggedIn) {
      logInorOut = (
        <DropdownItem
          key={5}
          tag="a"
          href="/account/logout"
          className='dropdown-menu--item'
        >
           <span className='content-3 ml-3'>Log Out</span>
        </DropdownItem>
      )

    } else {
      logInorOut =
        <DropdownItem
          key={2}
          tag="a"
          href="/account/login"
          className='dropdown-menu--item'
        >
          <span className='content-3 ml-3'>Log In</span>
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
