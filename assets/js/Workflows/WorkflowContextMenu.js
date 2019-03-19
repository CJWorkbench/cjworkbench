// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'

export default class WorkflowContextMenu extends React.Component {
  static propTypes = {
    deleteWorkflow: PropTypes.func.isRequired,
    duplicateWorkflow: PropTypes.func.isRequired,
    canDelete: PropTypes.bool.isRequired
  }

  renderDelete = () => {
    if (this.props.canDelete) {
      return (
        <DropdownItem onClick={this.props.deleteWorkflow} className='test-delete-button'>
          <i className="icon-bin"></i>
          <span>Delete</span>
        </DropdownItem>
      )
    }
  }

  render() {
    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='context-button--icon icon-more'></i>
        </DropdownToggle>
        <DropdownMenu positionFixed right>
          <DropdownItem onClick={this.props.duplicateWorkflow} className='test-duplicate-button'>
            <i className="icon-duplicate"></i>
            <span>Duplicate</span>
          </DropdownItem>
          {this.renderDelete()}
        </DropdownMenu>
      </UncontrolledDropdown>
    );
  }
}
