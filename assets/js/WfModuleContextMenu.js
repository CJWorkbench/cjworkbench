// Drop-down menu at upper right of each module in a workflow

import React from 'react'
import PropTypes from 'prop-types'
import {
    DropdownMenu,
    UncontrolledDropdown,
    DropdownToggle,
    DropdownItem,
  } from 'reactstrap'
import ExportModal from './ExportModal'


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
    let exportModal = null;
    if (this.state.exportModalOpen) {
      exportModal = <ExportModal id={this.props.id} onClose={this.toggleExportModal}/>
    }

    return (
       <UncontrolledDropdown onClick={this.props.stopProp}>
        <DropdownToggle title="more" className='context-button'>
          <i className='context-button--icon icon-more'></i>
        </DropdownToggle>
        <DropdownMenu right>
          {/* Opens Modal window for downloading files */}
          <DropdownItem key={1} onClick={this.toggleExportModal} className='test-export-button'>
            <i className='icon-download'></i>
            <span>Export</span>
            {exportModal}
          </DropdownItem>
          {/* Will delete the parent WF Module from the list */}
          <DropdownItem key={3} onClick={this.deleteOption} className='test-delete-button'>
            <i className='icon-bin'></i>
            <span>Delete</span>
          </DropdownItem>
        </DropdownMenu>
       </UncontrolledDropdown>
    );
  }
}

WfModuleContextMenu.propTypes = {
  removeModule: PropTypes.func,
  id:           PropTypes.number,
  stopProp:     PropTypes.func
};
