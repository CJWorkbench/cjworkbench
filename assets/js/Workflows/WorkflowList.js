import React from 'react'
import PropTypes from 'prop-types'
import Workflow from './Workflow'

const TextComparator = new Intl.Collator() // locale alphabetical

const Comparators = {
  'last_update|ascending': (a, b) => new Date(a.last_update) - new Date(b.last_update),
  'last_update|descending': (a, b) => new Date(b.last_update) - new Date(a.last_update),
  'name|ascending': (a, b) => TextComparator.compare(a.name, b.name),
  'name|descending': (a, b) => TextComparator.compare(b.name, a.name)
}

function WorkflowList ({ workflows, comparator, deleteWorkflow, duplicateWorkflow, openShareModal }) {
  const compare = Comparators[comparator]
  return (
    <div className='workflows-item--wrap'>
      {workflows.slice().sort(compare).map(workflow => (
        <Workflow
          workflow={workflow}
          key={workflow.id}
          deleteWorkflow={deleteWorkflow}
          duplicateWorkflow={duplicateWorkflow}
          openShareModal={openShareModal}
        />
      ))}
    </div>
  )
}
WorkflowList.propTypes = {
  workflows: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
  }).isRequired).isRequired,
  comparator: PropTypes.oneOf([ 'last_update|ascending', 'last_update|descending', 'name|ascending', 'name|descending' ]),
  deleteWorkflow: PropTypes.func, // func(id) => undefined, or null if not allowed to delete
  duplicateWorkflow: PropTypes.func.isRequired, // func(id) => undefined
  openShareModal: PropTypes.func, // func(id) => undefined
}
export default React.memo(WorkflowList)
