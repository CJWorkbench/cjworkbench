// "Hamburger" drop down on workflow and workflows page. Fixed contents.

import React from 'react'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap'
import PropTypes from 'prop-types'


export default class WfHamburgerMenu extends React.Component {

  render() {
    var homeLink, undoRedo;

    // If we are on the workflow page, we have undo and redo items
    if (this.props.workflowId != undefined) {
      homeLink =
        <DropdownItem
          key={1}
          tag="a"
          href="/workflows"
          className='dropdown-menu-item'
        >
          <span className='t-d-gray content-3 ml-3'>Your Workflows</span>
        </DropdownItem>;
      undoRedo =
        <div>
          <DropdownItem divider key={100} />
          <DropdownItem
            key={2}
            onClick={ () => { this.props.api.undo(this.props.workflowId)} }
            className='dropdown-menu-item'
          >
            <span className='t-d-gray content-3 ml-3'>Undo</span>
          </DropdownItem>
          <DropdownItem
            key={3}
            onClick={ () => { this.props.api.redo(this.props.workflowId)} }
            className='dropdown-menu-item'
          >
            <span className='t-d-gray content-3 ml-3'>Redo</span>
          </DropdownItem>
          <DropdownItem divider key={200} />
        </div>;
    }

    return (
       <UncontrolledDropdown>
        <DropdownToggle className="context-button">
          <div className='button-icon icon-more'></div>
        </DropdownToggle>
        <DropdownMenu right>
          { homeLink }
          { undoRedo }
          <DropdownItem
            key={4}
            tag="a"
            href="http://blog.cjworkbench.org"
            className='dropdown-menu-item'
          >
             <span className='t-d-gray content-3 ml-3'>Help</span>
          </DropdownItem>
          <DropdownItem
            key={5}
            tag="a"
            href="/account/logout"
            className='dropdown-menu-item'
          >
             <span className='t-d-gray content-3 ml-3'>Logout</span>
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WfHamburgerMenu.propTypes = {
  workflowId:   PropTypes.number,
  api:          PropTypes.object
};
