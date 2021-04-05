import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'
import { Trans } from '@lingui/macro'
import { timeDifference } from '../utils'
import WorkflowContextMenu from './WorkflowContextMenu'

function canOnlyViewReport (user, workflow) {
  if (workflow.public) {
    return false
  }

  if (user) {
    const aclEntry = workflow.acl.find(({ email }) => email === user.email)
    if (aclEntry && aclEntry.role === 'report-viewer') {
      return true
    }
  }

  return false
}

function WorkflowPrivacy (props) {
  const { workflow, user = null } = props

  if (workflow.public) {
    return <Trans id='js.Workflows.WorkflowMetadata.visibility.public'>public</Trans>
  }

  if (workflow.secret_id) {
    return <Trans id='js.Workflows.WorkflowMetadata.visibility.secret'>secret link</Trans>
  }

  if (canOnlyViewReport(user, workflow)) {
    return <Trans id='js.Workflows.WorkflowMetadata.visibility.privateReport'>private report</Trans>
  }

  return <Trans id='js.Workflows.WorkflowMetadata.visibility.private'>private</Trans>
}
WorkflowPrivacy.propTypes = {
  workflow: PropTypes.shape({
    public: PropTypes.bool.isRequired,
    acl: PropTypes.arrayOf(
      PropTypes.shape({
        email: PropTypes.string.isRequired,
        role: PropTypes.oneOf(['editor', 'viewer', 'report-viewer']).isRequired
      }).isRequired
    ).isRequired
  }),
  user: PropTypes.shape({
    email: PropTypes.string.isRequired
  }) // or null
}

export default function Workflow (props) {
  const {
    workflow,
    user,
    api = null,
    onWorkflowChanging = null,
    onWorkflowChanged = null,
    onWorkflowDuplicating = null,
    onWorkflowDuplicated = null,
    now = new Date().toISOString()
  } = props
  const timeAgo = timeDifference(workflow.last_update, now, i18n)
  const showActions = Boolean(api)

  const href = canOnlyViewReport(user, workflow)
    ? `/workflows/${workflow.id}/report`
    : `/workflows/${workflow.id}`

  return (
    <tr className={workflow.nPendingChanges ? 'changing' : null}>
      <td className='title'>
        <a href={href}>{workflow.name}</a>
      </td>
      <td className='owner'>
        <a href={href}>{workflow.owner_name}</a>
      </td>
      <td className='updated'>
        <a href={href}>
          <time dateTime={workflow.last_updated}>{timeAgo}</time>
        </a>
      </td>
      <td className='privacy'>
        <a href={href}>
          <WorkflowPrivacy workflow={workflow} user={user} />
        </a>
      </td>
      {showActions
        ? (
          <td className='actions'>
            <WorkflowContextMenu
              workflow={workflow}
              user={user}
              api={api}
              onWorkflowChanging={onWorkflowChanging}
              onWorkflowChanged={onWorkflowChanged}
              onWorkflowDuplicating={onWorkflowDuplicating}
              onWorkflowDuplicated={onWorkflowDuplicated}
            />
          </td>
          )
        : null}
    </tr>
  )
}
Workflow.propTypes = {
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    nPendingChanges: PropTypes.number // or undefined for 0
  }).isRequired,
  user: PropTypes.object, // or null
  now: PropTypes.string, // or null for current ISO8601 date (prop is useful for testing snapshots)
  onClickDeleteWorkflow: PropTypes.func, // func(id) => undefined, or null if not allowed to delete
  onClickDuplicateWorkflow: PropTypes.func, // func(id) => undefined, or null if user must _open_ to duplicate
  api: PropTypes.shape({
    deleteWorkflow: PropTypes.func.isRequired, // func(id) => Promise[null]
    duplicateWorkflow: PropTypes.func.isRequired, // func(id) => Promise[{ id, name }]
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, role) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublicAccess: PropTypes.func.isRequired // func(id, isPublic, hasSecret) => Promise[{workflow}]
  }), // or null if user is not allowed to change sharing settings
  onWorkflowChanging: PropTypes.func, // func(id, {k:v,...}) => undefined, or null if caller doesn't care
  onWorkflowChanged: PropTypes.func // func(id) => undefined, or null if caller doesn't care
}
