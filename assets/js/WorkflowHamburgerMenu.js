// "Hamburger" drop down on workflow and workflows page. Fixed contents.

import React from 'react'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap'
import PropTypes from 'prop-types'


export default class WorkflowHamburgerMenu extends React.Component {
  constructor(props) {
    super(props);
  }

  // \u2630 = hamburger menu in Unicode (actually, an I Ching trigram)
  render() {
    var homeLink;
    if (!this.props.workflowsPage)
      homeLink = <DropdownItem key={1} tag="a" href="/workflows"> Your Workflows </DropdownItem>;

    return (
       <UncontrolledDropdown>
        <DropdownToggle>
          {'\u2630'}
        </DropdownToggle>
        <DropdownMenu right>
          { homeLink }
          <DropdownItem key={2} tag="a" href="http://blog.cjworkbench.org"> Help </DropdownItem>
          <DropdownItem key={3} tag="a" href="/logout"> Logout </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WorkflowHamburgerMenu.propTypes = {
  workflowsPage:  PropTypes.bool,
};
