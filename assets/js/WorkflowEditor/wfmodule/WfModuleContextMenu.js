// Drop-down menu at upper right of each module in a workflow

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../../components/Dropdown'
import ExportModal from '../../ExportModal'

export default class WfModuleContextMenu extends React.Component {
  constructor (props) {
    super(props)
    this.deleteOption = this.deleteOption.bind(this)
    this.toggleExportModal = this.toggleExportModal.bind(this)

    this.state = {
      exportModalOpen: false
    }
  }

  deleteOption () {
    this.props.removeModule()
  }

  toggleExportModal () {
    this.setState({ exportModalOpen: !this.state.exportModalOpen })
  }

  render () {
    return (
      <UncontrolledDropdown>
        <DropdownToggle title='more' className='context-button'>
          <i className='icon-more' />
        </DropdownToggle>
        <DropdownMenu>
          <DropdownItem onClick={this.toggleExportModal} className='test-export-button' icon='icon-download'>Export data</DropdownItem>
          <DropdownItem onClick={this.deleteOption} className='test-delete-button' icon='icon-bin'>Delete</DropdownItem>
        </DropdownMenu>
        <ExportModal open={this.state.exportModalOpen} wfModuleId={this.props.id} toggle={this.toggleExportModal} />
      </UncontrolledDropdown>
    )
  }
}

WfModuleContextMenu.propTypes = {
  removeModule: PropTypes.func,
  id: PropTypes.number
}
