// Drop-down menu on Workflows List page, for each listed WF
// triggered by click on three-dot icon next to listed workflow

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'

export default class WorkflowContextMenu extends React.Component {
  static propTypes = {
    workflowId: PropTypes.number.isRequired,
    deleteWorkflow: PropTypes.func, // func(id) ... or null if cannot delete
    duplicateWorkflow: PropTypes.func.isRequired
  }

  onClickDelete = () => {
    const { workflowId, deleteWorkflow } = this.props
    if (deleteWorkflow) deleteWorkflow(workflowId)
  }

  onClickDuplicate = () => {
    const { workflowId, duplicateWorkflow } = this.props
    duplicateWorkflow(workflowId)
  }

  render() {
    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='icon-more'></i>
        </DropdownToggle>
        <DropdownMenu>
          <DropdownItem onClick={this.onClickDuplicate} className='duplicate-workflow'>
            <i className="icon-duplicate"></i>
            <span>Duplicate</span>
          </DropdownItem>
          {this.props.deleteWorkflow ? (
            <DropdownItem onClick={this.onClickDelete} className='delete-workflow'>
              <i className="icon-bin"></i>
              <span>Delete</span>
            </DropdownItem>
          ) : null}
        </DropdownMenu>
      </UncontrolledDropdown>
    );
  }
}
