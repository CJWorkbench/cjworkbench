import React from 'react'
import PropTypes from 'prop-types'
import DropdownToggle from 'reactstrap/lib/DropdownToggle'
import DropdownMenu from 'reactstrap/lib/DropdownMenu'
import DropdownItem from 'reactstrap/lib/DropdownItem'
import UncontrolledDropdown from 'reactstrap/lib/UncontrolledDropdown'

export default function TabContextMenu ({ onClickRename, onClickDelete }) {
  return (
    <UncontrolledDropdown direction='up'>
      <DropdownToggle className='toggle'>
        <i className="icon-caret-down"/>
      </DropdownToggle>
      <DropdownMenu positionFixed right>
        <div className="dropdown-items-container">
          <DropdownItem onClick={onClickRename}><i className='icon-edit'></i> Rename</DropdownItem>
          <DropdownItem onClick={onClickDelete}><i className='icon-removec'></i> Delete</DropdownItem>
        </div>
      </DropdownMenu>
    </UncontrolledDropdown>
  )
}
