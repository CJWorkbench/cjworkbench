import React from 'react'
import PropTypes from 'prop-types'
import {
  UncontrolledDropdown,
  DropdownToggle,
  DropdownMenu,
  DropdownItem
} from '../components/Dropdown'
import { Trans } from '@lingui/macro'

const RoleLabel = ({ role }) => {
  if (role === 'editor') {
    return <Trans id='js.ShareModal.Role.editor'>Can edit</Trans>
  } else if (role === 'viewer') {
    return <Trans id='js.ShareModal.Role.viewer'>Can view</Trans>
  } else if (role === 'report-viewer') {
    return <Trans id='js.ShareModal.Role.report-viewer'>Can only view report</Trans>
  } else {
    return '???'
  }
}

const EditableRole = ({ role, onChange }) => {
  const handleClickRole = React.useCallback(ev => {
    if (ev.target.value !== role) {
      onChange(ev.target.value)
    }
  }, [role, onChange])

  return (
    <UncontrolledDropdown>
      <DropdownToggle caret>
        <RoleLabel role={role} />
      </DropdownToggle>
      <DropdownMenu>
        <DropdownItem
          onClick={handleClickRole}
          active={role === 'editor'}
          name='role'
          value='editor'
        >
          <Trans id='js.ShareModal.Role.editor'>Can edit</Trans>
        </DropdownItem>
        <DropdownItem
          onClick={handleClickRole}
          active={role === 'viewer'}
          name='role'
          value='viewer'
        >
          <Trans id='js.ShareModal.Role.viewer'>Can view</Trans>
        </DropdownItem>
        <DropdownItem
          onClick={handleClickRole}
          active={role === 'report-viewer'}
          name='role'
          value='report-viewer'
        >
          <Trans id='js.ShareModal.Role.report-viewer'>Can only view report</Trans>
        </DropdownItem>
      </DropdownMenu>
    </UncontrolledDropdown>
  )
}

export default function Role (props) {
  const { isReadOnly, role, onChange } = props

  if (isReadOnly) {
    return <p className='role'><RoleLabel role={role} /></p>
  } else {
    return <EditableRole role={role} onChange={onChange} />
  }
}
Role.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  role: PropTypes.oneOf(['editor', 'viewer', 'report-viewer']).isRequired,
  onChange: PropTypes.func.isRequired // func(role) => undefined
}
