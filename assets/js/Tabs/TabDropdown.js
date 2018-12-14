import React from 'react'
import PropTypes from 'prop-types'
import DropdownToggle from 'reactstrap/lib/DropdownToggle'
import DropdownMenu from 'reactstrap/lib/DropdownMenu'
import DropdownItem from 'reactstrap/lib/DropdownItem'
import UncontrolledDropdown from 'reactstrap/lib/UncontrolledDropdown'

export default function TabContextMenu ({ onClickRename, onClickDelete }) {
  return (
    <UncontrolledDropdown direction='up'>
      <DropdownToggle caret color='link'></DropdownToggle>
      <DropdownMenu positionFixed>
        <DropdownItem onClick={onClickRename}><i className='icon-rename'></i> Rename</DropdownItem>
        <DropdownItem onClick={onClickDelete}><i className='icon-delete'></i> Delete</DropdownItem>
      </DropdownMenu>
    </UncontrolledDropdown>
  )
}
