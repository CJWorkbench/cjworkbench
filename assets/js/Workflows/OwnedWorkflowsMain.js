/* globals confirm */
import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import WorkflowList, { WorkflowListPropType } from './WorkflowList'
import CreateWorkflowButton from './CreateWorkflowButton'

function beginEdit (edits, id, changes) {
  const edit = edits[id]
    ? { changes: { ...edits[id].changes, ...changes }, nPendingChanges: edits[id].nPendingChanges + 1 }
    : { changes, nPendingChanges: 1 }
  return { ...edits, [id]: edit }
}

function endEdit (edits, id) {
  const edit = { ...edits[id], nPendingChanges: edits[id].nPendingChanges - 1 }
  return { ...edits, [id]: edit }
}

function reduceWorkflowEdit (state, action) {
  const { adds, edits } = state
  switch (action.type) {
    case 'begin-edit': {
      const { id, changes } = action.payload
      return { adds, edits: beginEdit(edits, id, changes) }
    }
    case 'end-edit': {
      const { id } = action.payload
      return { adds, edits: endEdit(edits, id) }
    }
    case 'begin-duplicate': {
      const { id } = action.payload
      return { adds, edits: beginEdit(edits, id, {}) }
    }
    case 'end-duplicate': {
      const { id, workflow } = action.payload
      return { adds: [workflow, ...adds], edits: endEdit(edits, id) }
    }
  }
}

/**
 * Keep a local cache of pending/completed edits.
 *
 * To edit a workflow, call `handleWorkflowChanging(id, { public: true })` and
 * then submit the API request. When the request completes, call
 * `handleWorkflowChanged(id)`.
 *
 * This isn't theoretically perfect: if edit B reaches the server before edit A,
 * then we'll locally assume edit A succeeded, even if remotely edit B came
 * last. TODO serialize requests or implement more complex logic.
 */
function useWorkflowEdits (workflows) {
  const [state, dispatch] = React.useReducer(reduceWorkflowEdit, { adds: [], edits: {} })

  const handleWorkflowChanging = React.useCallback((id, changes) => {
    dispatch({ type: 'begin-edit', payload: { id, changes } })
  }, [dispatch])
  const handleWorkflowChanged = React.useCallback(id => {
    dispatch({ type: 'end-edit', payload: { id } })
  }, [dispatch])
  const handleWorkflowDuplicating = React.useCallback(id => {
    dispatch({ type: 'begin-duplicate', payload: { id } })
  }, [dispatch])
  const handleWorkflowDuplicated = React.useCallback((id, workflow) => {
    dispatch({ type: 'end-duplicate', payload: { id, workflow } })
  }, [dispatch])

  const { adds, edits } = state
  const editedWorkflows = adds.concat(workflows).map(workflow => {
    const entry = edits[workflow.id]
    return entry
      ? { ...workflow, ...entry.changes, nPendingChanges: entry.nPendingChanges }
      : workflow
  }).filter(workflow => !workflow.isDeleted || workflow.nPendingChanges > 0)

  return {
    editedWorkflows,
    handleWorkflowChanging,
    handleWorkflowChanged,
    handleWorkflowDuplicating,
    handleWorkflowDuplicated
  }
}

export default function OwnedWorkflowsMain (props) {
  const { api, workflows } = props

  const {
    editedWorkflows,
    handleWorkflowChanging,
    handleWorkflowChanged,
    handleWorkflowDuplicating,
    handleWorkflowDuplicated
  } = useWorkflowEdits(workflows)

  const handleClickDeleteWorkflow = React.useCallback(id => {
    if (!confirm(
      t({ id: 'js.Workflows.delete.permanentyDeleteWarning', message: 'Permanently delete this workflow?' })
    )) {
      return
    }

    handleWorkflowChanging(id, { isDeleted: true })
    api.deleteWorkflow(id).then(() => handleWorkflowChanged(id))
  }, [api, handleWorkflowChanging, handleWorkflowChanged])

  const handleClickDuplicateWorkflow = React.useCallback(id => {
    handleWorkflowDuplicating(id, {})
    api.duplicateWorkflow(id).then(json => {
      handleWorkflowDuplicated(id, json)
    })
  }, [api, handleWorkflowDuplicating, handleWorkflowDuplicated])

  return (
    <main className='workflows'>
      <header>
        <h1><Trans id='js.Workflows.WorkflowLists.nav.myWorkflows'>My workflows</Trans></h1>
      </header>
      {editedWorkflows.length ? (
        <WorkflowList
          className='owned'
          workflows={editedWorkflows}
          onClickDeleteWorkflow={handleClickDeleteWorkflow}
          onClickDuplicateWorkflow={handleClickDuplicateWorkflow}
          apiForShareModal={api}
          onWorkflowChanging={handleWorkflowChanging}
          onWorkflowChanged={handleWorkflowChanged}
        />
      ) : (
        <CreateWorkflowButton>
          <Trans id='js.Workflows.WorkflowLists.createYourFirtsWorkflow.button'>Create your first workflow</Trans>
        </CreateWorkflowButton>
      )}
    </main>
  )
}
OwnedWorkflowsMain.propTypes = {
  workflows: WorkflowListPropType.isRequired,
  api: PropTypes.shape({
    deleteWorkflow: PropTypes.func.isRequired, // func(id) => Promise[null]
    duplicateWorkflow: PropTypes.func.isRequired, // func(id) => Promise[{ id, name }]
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, canEdit) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublic: PropTypes.func.isRequired // func(id, isPublic) => Promise[null]
  }).isRequired
}
