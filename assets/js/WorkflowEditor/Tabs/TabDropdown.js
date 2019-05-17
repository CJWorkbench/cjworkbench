import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../../components/Dropdown'

export default function TabDropdown ({ onClickRename, onClickDelete, onClickDuplicate }) {
  return (
    <UncontrolledDropdown>
      <DropdownToggle className='toggle'>
        <i className='icon-caret-down'/>
      </DropdownToggle>
      <DropdownMenu>
        <DropdownItem onClick={onClickRename} icon='icon-edit'>Rename</DropdownItem>
        <DropdownItem onClick={onClickDuplicate} icon='icon-duplicate'>Duplicate</DropdownItem>
        <DropdownItem onClick={onClickDelete} icon='icon-removec'>Delete</DropdownItem>
      </DropdownMenu>
    </UncontrolledDropdown>
  )
}
