import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../components/Modal'
import { Trans } from '@lingui/macro'
import PublicAccess from './PublicAccess'
import CollaboratorAccess from './CollaboratorAccess'

export default function _Modal (props) {
  const {
    isReadOnly,
    canCreateSecretLink,
    isPublic,
    secretId,
    setWorkflowPublicAccess,
    ownerEmail,
    acl,
    updateAclEntry,
    deleteAclEntry,
    onClickClose,
    workflowId
  } = props

  return (
    <Modal className='share-modal' isOpen toggle={onClickClose}>
      <ModalHeader>
        <Trans
          id='js.ShareModal.Modal.header.title'
          comment='This should be all-caps for styling reasons'
        >
          SHARE WORKFLOW
        </Trans>
      </ModalHeader>
      <ModalBody>
        <CollaboratorAccess
          isReadOnly={isReadOnly}
          ownerEmail={ownerEmail}
          isPublic={isPublic}
          acl={acl}
          updateAclEntry={updateAclEntry}
          deleteAclEntry={deleteAclEntry}
        />
        <hr />
        <PublicAccess
          workflowId={workflowId}
          isPublic={isPublic}
          isReadOnly={isReadOnly}
          secretId={secretId}
          canCreateSecretLink={canCreateSecretLink}
          setWorkflowPublicAccess={setWorkflowPublicAccess}
        />
      </ModalBody>
      <ModalFooter>
        <div className='actions'>
          <button
            name='close'
            className='action-button button-gray'
            onClick={onClickClose}
          >
            <Trans id='js.ShareModal.Modal.footer.closeButton'>Close</Trans>
          </button>
        </div>
      </ModalFooter>
    </Modal>
  )
}
_Modal.propTypes = {
  isReadOnly: PropTypes.bool.isRequired, // are we owner? Otherwise, we can't edit the ACL
  workflowId: PropTypes.number.isRequired,
  isPublic: PropTypes.bool.isRequired,
  secretId: PropTypes.string.isRequired, // "" for no secret ID
  canCreateSecretLink: PropTypes.bool.isRequired,
  ownerEmail: PropTypes.string.isRequired,
  acl: PropTypes.arrayOf(
    PropTypes.shape({
      email: PropTypes.string.isRequired,
      role: PropTypes.oneOf(['editor', 'viewer', 'report-viewer']).isRequired
    }).isRequired
  ), // or null if loading
  setWorkflowPublicAccess: PropTypes.func.isRequired, // func(isPublic, hasSecret) => Promise[undefined]
  updateAclEntry: PropTypes.func.isRequired, // func(email, role) => undefined
  deleteAclEntry: PropTypes.func.isRequired, // func(email) => undefined
  onClickClose: PropTypes.func.isRequired // func() => undefined
}
