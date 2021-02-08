import React from 'react'
import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'
import { Trans } from '@lingui/macro'
import { timeDifference } from '../utils'
import WorkflowContextMenu from './WorkflowContextMenu'

export default function Workflow (props) {
  const {
    workflow,
    api = null,
    onWorkflowChanging = null,
    onWorkflowChanged = null,
    onWorkflowDuplicating = null,
    onWorkflowDuplicated = null,
    now = new Date().toISOString()
  } = props
  const timeAgo = timeDifference(workflow.last_update, now, i18n)
  const showActions = Boolean(api)

  return (
    <tr className={workflow.nPendingChanges ? 'changing' : null}>
      <td className='title'><a href={`/workflows/${workflow.id}`}>{workflow.name}</a></td>
      <td className='owner'><a href={`/workflows/${workflow.id}`}>{workflow.owner_name}</a></td>
      <td className='updated'>
        <a href={`/workflows/${workflow.id}`}>
          <time dateTime={workflow.last_updated}>{timeAgo}</time>
        </a>
      </td>
      <td className='privacy'>
        <a href={`/workflows/${workflow.id}`}>
          {workflow.public ? (
            <Trans id='js.Workflows.WorkflowMetadata.visibility.public'>public</Trans>
          ) : (
            <Trans id='js.Workflows.WorkflowMetadata.visibility.private'>private</Trans>
          )}
        </a>
      </td>
      {showActions ? (
        <td className='actions'>
          <WorkflowContextMenu
            workflow={workflow}
            api={api}
            onWorkflowChanging={onWorkflowChanging}
            onWorkflowChanged={onWorkflowChanged}
            onWorkflowDuplicating={onWorkflowDuplicating}
            onWorkflowDuplicated={onWorkflowDuplicated}
          />
        </td>
      ) : null}
    </tr>
  )
}
Workflow.propTypes = {
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    nPendingChanges: PropTypes.number // or undefined for 0
  }).isRequired,
  now: PropTypes.string, // or null for current ISO8601 date (prop is useful for testing snapshots)
  onClickDeleteWorkflow: PropTypes.func, // func(id) => undefined, or null if not allowed to delete
  onClickDuplicateWorkflow: PropTypes.func, // func(id) => undefined, or null if user must _open_ to duplicate
  api: PropTypes.shape({
    deleteWorkflow: PropTypes.func.isRequired, // func(id) => Promise[null]
    duplicateWorkflow: PropTypes.func.isRequired, // func(id) => Promise[{ id, name }]
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, canEdit) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublic: PropTypes.func.isRequired // func(id, isPublic) => Promise[null]
  }), // or null if user is not allowed to change sharing settings
  onWorkflowChanging: PropTypes.func, // func(id, {k:v,...}) => undefined, or null if caller doesn't care
  onWorkflowChanged: PropTypes.func // func(id) => undefined, or null if caller doesn't care
}
