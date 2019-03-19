import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'

export default function TabContextMenu ({ onClickRename, onClickDelete }) {
  return (
    <UncontrolledDropdown direction='up'>
      <DropdownToggle className='toggle'>
        <i className='icon-caret-up'/>
      </DropdownToggle>
      <DropdownMenu positionFixed right>
        <DropdownItem onClick={onClickRename}><i className='icon-edit'></i> Rename</DropdownItem>
        <DropdownItem onClick={onClickDelete}><i className='icon-removec'></i> Delete</DropdownItem>
      </DropdownMenu>
    </UncontrolledDropdown>
  )
}
