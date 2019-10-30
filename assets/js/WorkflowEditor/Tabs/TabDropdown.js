import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../../components/Dropdown'
import { Trans } from '@lingui/macro'

export default function TabDropdown ({ onClickRename, onClickDelete, onClickDuplicate }) {
  return (
    <UncontrolledDropdown>
      <DropdownToggle className='toggle'>
        <i className='icon-caret-down' />
      </DropdownToggle>
      <DropdownMenu>
        <DropdownItem onClick={onClickRename} icon='icon-edit'><Trans id='workflow.rename'>Rename</Trans></DropdownItem>
        <DropdownItem onClick={onClickDuplicate} icon='icon-duplicate'><Trans id='workflow.duplicate'>Duplicate</Trans></DropdownItem>
        <DropdownItem onClick={onClickDelete} icon='icon-removec'><Trans id='workflow.deleteEvent'>Delete</Trans></DropdownItem>
      </DropdownMenu>
    </UncontrolledDropdown>
  )
}
TabDropdown.propTypes = {
  onClickRename: PropTypes.func.isRequired, // func() => undefined
  onClickDuplicate: PropTypes.func.isRequired, // func() => undefined
  onClickDelete: PropTypes.func.isRequired // func() => undefined
}
