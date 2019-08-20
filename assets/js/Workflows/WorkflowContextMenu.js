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

  handleClickDelete = () => {
    const { workflowId, deleteWorkflow } = this.props
    if (deleteWorkflow) deleteWorkflow(workflowId)
  }

  handleClickDuplicate = () => {
    const { workflowId, duplicateWorkflow } = this.props
    duplicateWorkflow(workflowId)
  }

  render () {
    return (
      <UncontrolledDropdown>
        <DropdownToggle className='context-button'>
          <i className='icon-more' />
        </DropdownToggle>
        <DropdownMenu>
          <DropdownItem onClick={this.handleClickDuplicate} className='duplicate-workflow'>
            <i className='icon-duplicate' />
            <span>Duplicate</span>
          </DropdownItem>
          {this.props.deleteWorkflow ? (
            <DropdownItem onClick={this.handleClickDelete} className='delete-workflow'>
              <i className='icon-bin' />
              <span>Delete</span>
            </DropdownItem>
          ) : null}
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}
