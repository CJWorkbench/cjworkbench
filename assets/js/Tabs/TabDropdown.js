import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'

export default function TabContextMenu ({ onClickRename, onClickDelete }) {
  return (
    <UncontrolledDropdown>
      <DropdownToggle className='toggle'>
        <i className='icon-caret-up'/>
      </DropdownToggle>
      <DropdownMenu>
        <DropdownItem onClick={onClickRename} icon='icon-edit'>Rename</DropdownItem>
        <DropdownItem onClick={onClickDelete} icon='icon-removec'>Delete</DropdownItem>
      </DropdownMenu>
    </UncontrolledDropdown>
  )
}
