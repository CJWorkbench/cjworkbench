import React from 'react'
import PropTypes from 'prop-types'
import Role from './Role'

export default function AclEntry (props) {
  const { isReadOnly, email, role, updateAclEntry, deleteAclEntry } = props

  const handleChangeRole = React.useCallback(
    newRole => { updateAclEntry(email, newRole) },
    [updateAclEntry, email]
  )

  const handleClickDelete = React.useCallback(
    () => { deleteAclEntry(email) },
    [deleteAclEntry, email]
  )

  return (
    <div className='acl-entry'>
      <div className='email'>{email}</div>
      <Role
        role={role}
        isReadOnly={isReadOnly}
        onChange={handleChangeRole}
        onClickDelete={handleClickDelete}
      />
    </div>
  )
}
AclEntry.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  email: PropTypes.string.isRequired,
  role: PropTypes.oneOf(['editor', 'viewer', 'report-viewer']).isRequired,
  updateAclEntry: PropTypes.func.isRequired, // func(email, role) => undefined
  deleteAclEntry: PropTypes.func.isRequired // func(email) => undefined
}
