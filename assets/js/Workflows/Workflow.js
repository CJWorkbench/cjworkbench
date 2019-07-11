import React from 'react'
import PropTypes from 'prop-types'
import WorkflowContextMenu from './WorkflowContextMenu'
import WorkflowMetadata from './WorkflowMetadata'

function Workflow ({ workflow, deleteWorkflow, duplicateWorkflow, openShareModal }) {
  return (
    <div className='workflow'>
      <a href={`/workflows/${workflow.id}`}>
        <div className='workflow-title'>{workflow.name}</div>
        <WorkflowMetadata
          workflow={workflow}
          openShareModal={openShareModal}
        />
      </a>
      <WorkflowContextMenu
        workflowId={workflow.id}
        duplicateWorkflow={duplicateWorkflow}
        deleteWorkflow={deleteWorkflow}
      />
    </div>
  )
}
Workflow.propTypes = {
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired
  }).isRequired,
  deleteWorkflow: PropTypes.func, // func(id) => undefined, or null if not allowed to delete
  duplicateWorkflow: PropTypes.func.isRequired, // func(id) => undefined
  openShareModal: PropTypes.func // func(id) => undefined
}
export default React.memo(Workflow)
