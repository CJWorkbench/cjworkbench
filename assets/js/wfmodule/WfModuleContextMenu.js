// Drop-down menu at upper right of each module in a workflow

import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'
import ExportModal from '../ExportModal'


export default class WfModuleContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.deleteOption = this.deleteOption.bind(this);
    this.toggleExportModal = this.toggleExportModal.bind(this);

    this.state = {
      exportModalOpen: false,
    };
  }

  deleteOption() {
    this.props.removeModule();
  }

  toggleExportModal() {
    this.setState({ exportModalOpen: !this.state.exportModalOpen });
  }

  render() {

    return (
       <UncontrolledDropdown>
        <DropdownToggle title="more" className='context-button'>
          <i className='context-button--icon icon-more'></i>
        </DropdownToggle>
        <DropdownMenu positionFixed right>
          <DropdownItem key={1} onClick={this.toggleExportModal} className='test-export-button'>
            <i className='icon-download'></i>
            <span>Export data</span>
            <ExportModal open={this.state.exportModalOpen} wfModuleId={this.props.id} onClose={this.toggleExportModal}/>
          </DropdownItem>

          <DropdownItem key={2} onClick={this.deleteOption} className='test-delete-button'>
            <i className='icon-bin'></i>
            <span>Delete</span>
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    )
  }
}

WfModuleContextMenu.propTypes = {
  removeModule: PropTypes.func,
  id:           PropTypes.number,
};
