import { useCallback } from 'react'
import PropTypes from 'prop-types'
import { logUserEvent } from '../utils'
import Modal from '../ShareModal/Modal'

function logShare (type) {
  logUserEvent('Share workflow ' + type)
}

export default function ShareModal (props) {
  const {
    api,
    workflow,
    onWorkflowChanging,
    onWorkflowChanged,
    onClose
  } = props

  const setIsPublic = useCallback(
    isPublic => {
      onWorkflowChanging(workflow.id, { public: isPublic })
      api
        .setWorkflowPublic(workflow.id, isPublic)
        .then(() => onWorkflowChanged(workflow.id))
    },
    [api, workflow, onWorkflowChanging, onWorkflowChanged]
  )
  const updateAclEntry = useCallback(
    (email, canEdit) => {
      onWorkflowChanging(workflow.id, {
        acl: [
          ...workflow.acl.filter(e => e.email !== email),
          { email, canEdit }
        ]
      })
      api
        .updateAclEntry(workflow.id, email, canEdit)
        .then(() => onWorkflowChanged(workflow.id))
    },
    [api, workflow, onWorkflowChanging, onWorkflowChanged]
  )
  const deleteAclEntry = useCallback(
    (email, canEdit) => {
      onWorkflowChanging(workflow.id, {
        acl: workflow.acl.filter(e => e.email !== email)
      })
      api
        .deleteAclEntry(workflow.id, email)
        .then(() => onWorkflowChanged(workflow.id))
    },
    [api, workflow, onWorkflowChanging, onWorkflowChanged]
  )

  return (
    <Modal
      isReadOnly={false}
      url={`${window.location.origin}/workflows/${workflow.id}`}
      isPublic={workflow.public}
      logShare={logShare}
      ownerEmail={workflow.owner_email}
      acl={workflow.acl}
      setIsPublic={setIsPublic}
      updateAclEntry={updateAclEntry}
      deleteAclEntry={deleteAclEntry}
      onClickClose={onClose}
    />
  )
}
ShareModal.propTypes = {
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired,
    owner_email: PropTypes.string.isRequired,
    public: PropTypes.bool.isRequired,
    acl: PropTypes.arrayOf(
      PropTypes.shape({
        email: PropTypes.string.isRequired,
        canEdit: PropTypes.bool.isRequired
      }).isRequired
    ).isRequired
  }).isRequired,
  api: PropTypes.shape({
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, canEdit) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublic: PropTypes.func.isRequired // func(id, isPublic) => Promise[null]
  }).isRequired, // or null if user is not allowed to change sharing settings
  onWorkflowChanged: PropTypes.func, // func(id, isPublic) => undefined, or null if we don't care
  onClose: PropTypes.func.isRequired
}
