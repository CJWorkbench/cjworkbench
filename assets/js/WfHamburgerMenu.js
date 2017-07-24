// "Hamburger" drop down on workflow and workflows page. Fixed contents.

import React from 'react'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap'
import PropTypes from 'prop-types'


export default class WfHamburgerMenu extends React.Component {

  render() {
    var homeLink, undoRedo;

    // If we are on the workflow page, we have undo and redo items
    if (this.props.workflowId != undefined) {
      homeLink = <DropdownItem key={1} tag="a" href="/workflows"> Your Workflows </DropdownItem>;
      undoRedo =
        <div>
          <DropdownItem divider key={100} />
          <DropdownItem key={2} onClick={ () => { this.props.api.undo(this.props.workflowId)} } > Undo </DropdownItem>
          <DropdownItem key={3} onClick={ () => { this.props.api.redo(this.props.workflowId)} } > Redo </DropdownItem>
          <DropdownItem divider key={200} />
        </div>;
    }

    // \u2630 = hamburger menu in Unicode (actually, an I Ching trigram)

    return (
       <UncontrolledDropdown>
        {/*<DropdownToggle className='icon-more'>*/}
        <DropdownToggle>
          {'\u2630'}
        </DropdownToggle>
        <DropdownMenu left>
          { homeLink }
          { undoRedo }
          <DropdownItem key={4} tag="a" href="http://blog.cjworkbench.org"> Help </DropdownItem>
          <DropdownItem key={5} tag="a" href="/account/logout"> Logout </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WfHamburgerMenu.propTypes = {
  workflowId:   PropTypes.number,
  api:          PropTypes.object
};
