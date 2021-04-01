import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import Acl from './Acl'
import ShareUrl from '../components/ShareUrl'

export default function CollaboratorAccess (props) {
  const { isReadOnly, workflowId, ownerEmail, acl, updateAclEntry, deleteAclEntry } = props
  const url = `${window.origin}/workflows/${workflowId}`

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
      </fieldset>

      {acl.length
        ? (
          <div className='shareable-link'>
            <h6>
              <Trans id='js.ShareModal.Modal.shareWithCollaborators'>Link for collaborators</Trans>
            </h6>
            <ShareUrl url={url} />
          </div>
          )
        : null}
    </>
  )
}
CollaboratorAccess.propTypes = {
  isReadOnly: PropTypes.bool.isRequired, // are we owner? Otherwise, we can't edit the ACL
  workflowId: PropTypes.number.isRequired,
  ownerEmail: PropTypes.string.isRequired,
  isPublic: PropTypes.bool.isRequired,
  acl: PropTypes.array.isRequired,
  updateAclEntry: PropTypes.func.isRequired, // func(email, role) => undefined
  deleteAclEntry: PropTypes.func.isRequired // func(email) => undefined
}
