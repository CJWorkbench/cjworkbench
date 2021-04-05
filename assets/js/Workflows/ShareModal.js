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
    canCreateSecretLink,
    onWorkflowChanging,
    onWorkflowChanged,
    onClose
  } = props

  const setPublicAccess = useCallback(
    (isPublic, hasSecret) => {
      onWorkflowChanging(workflow.id, { public: isPublic })
      return api
        .setWorkflowPublicAccess(workflow.id, isPublic, hasSecret)
        .then(json => onWorkflowChanged(workflow.id, json.workflow))
    },
    [api, workflow, onWorkflowChanging, onWorkflowChanged]
  )
  const updateAclEntry = useCallback(
    (email, role) => {
      onWorkflowChanging(workflow.id, {
        acl: [
          ...workflow.acl.filter(e => e.email !== email),
          { email, role }
        ]
      })
      api
        .updateAclEntry(workflow.id, email, role)
        .then(() => onWorkflowChanged(workflow.id))
    },
    [api, workflow, onWorkflowChanging, onWorkflowChanged]
  )
  const deleteAclEntry = useCallback(
    (email, role) => {
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
      canCreateSecretLink={canCreateSecretLink}
      url={`${window.location.origin}/workflows/${workflow.id}`}
      workflowId={workflow.id}
      isPublic={workflow.public}
      secretId={workflow.secret_id}
      logShare={logShare}
      ownerEmail={workflow.owner_email}
      acl={workflow.acl}
      setWorkflowPublicAccess={setPublicAccess}
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
    secret_id: PropTypes.string.isRequired,
    acl: PropTypes.arrayOf(
      PropTypes.shape({
        email: PropTypes.string.isRequired,
        role: PropTypes.oneOf(['editor', 'viewer', 'report-viewer']).isRequired
      }).isRequired
    ).isRequired
  }).isRequired,
  canCreateSecretLink: PropTypes.bool.isRequired,
  api: PropTypes.shape({
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, role) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublicAccess: PropTypes.func.isRequired // func(id, isPublic, hasSecret) => Promise[{workflow}]
  }).isRequired, // or null if user is not allowed to change sharing settings
  onWorkflowChanged: PropTypes.func, // func(id, isPublic) => undefined, or null if we don't care
  onClose: PropTypes.func.isRequired
}
