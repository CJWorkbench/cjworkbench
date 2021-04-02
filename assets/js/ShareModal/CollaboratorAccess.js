import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import Acl from './Acl'

export default function CollaboratorAccess (props) {
  const { isReadOnly, ownerEmail, acl, updateAclEntry, deleteAclEntry } = props

  return (
    <>
      <fieldset className='share-collaborators'>
        <legend>
          <Trans id='js.ShareModal.Modal.collaborators'>Collaborators</Trans>
        </legend>
        <Acl
          isReadOnly={isReadOnly}
          ownerEmail={ownerEmail}
          acl={acl}
          updateAclEntry={updateAclEntry}
          deleteAclEntry={deleteAclEntry}
        />

        {acl.length
          ? (
            <p className='description'>
              <Trans id='js.ShareModal.CollaboratorAccess.description'>Collaborators can log in and open “Shared with me” to find this workflow.</Trans>
            </p>
            )
          : null}
      </fieldset>
    </>
  )
}
CollaboratorAccess.propTypes = {
  isReadOnly: PropTypes.bool.isRequired, // are we owner? Otherwise, we can't edit the ACL
  ownerEmail: PropTypes.string.isRequired,
  isPublic: PropTypes.bool.isRequired,
  acl: PropTypes.array.isRequired,
  updateAclEntry: PropTypes.func.isRequired, // func(email, role) => undefined
  deleteAclEntry: PropTypes.func.isRequired // func(email) => undefined
}
