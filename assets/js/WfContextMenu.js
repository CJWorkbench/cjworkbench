// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import PropTypes from 'prop-types'
import UncontrolledDropdown from 'reactstrap/lib/UncontrolledDropdown'
import DropdownToggle from 'reactstrap/lib/DropdownToggle'
import DropdownMenu from 'reactstrap/lib/DropdownMenu'
import DropdownItem from 'reactstrap/lib/DropdownItem'

export default class WfContextMenu extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='context-button--icon icon-more'></i>
        </DropdownToggle>
        <DropdownMenu right>
          <DropdownItem onClick={this.props.duplicateWorkflow} className='test-duplicate-button'>
            <i className="icon-duplicate"></i>
            <span>Duplicate</span>
          </DropdownItem>
          <DropdownItem onClick={this.props.deleteWorkflow} className='test-delete-button'>
            <i className="icon-bin"></i>
            <span>Delete</span>
          </DropdownItem>
        </DropdownMenu>
      </UncontrolledDropdown>
    );
  }
}

WfContextMenu.propTypes = {
  deleteWorkflow:     PropTypes.func.isRequired,
  duplicateWorkflow:  PropTypes.func.isRequired
};
