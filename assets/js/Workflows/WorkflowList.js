import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import Workflow from './Workflow'
import SortAscendingIcon from '../../icons/sort-ascending.svg'
import SortDescendingIcon from '../../icons/sort-descending.svg'

const WorkflowListPropType = PropTypes.arrayOf(PropTypes.shape({
  id: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  last_update: PropTypes.string.isRequired // ISO8601 String
}).isRequired)
export { WorkflowListPropType }

function SortableColumnName (props) {
  const { sort, sortKey, defaultAscending, onChangeSort, children } = props

  const handleClickSort = React.useCallback(ev => {
    ev.preventDefault()
    const ascending = sort.key === sortKey ? !sort.ascending : defaultAscending
    onChangeSort({ key: sortKey, ascending })
  }, [sort, sortKey, defaultAscending, onChangeSort])

  return (
    <a href='#' onClick={handleClickSort}>
      {children}
      {sort.key === sortKey ? (
        sort.ascending ? <SortAscendingIcon /> : <SortDescendingIcon />
      ) : null}
    </a>
  )
}
SortableColumnName.propTypes = {
  sort: PropTypes.shape({
    key: PropTypes.string.isRequired,
    ascending: PropTypes.bool.isRequired
  }).isRequired, // what the user has sorted
  sortKey: PropTypes.string.isRequired, // this column key
  defaultAscending: PropTypes.bool.isRequired, // true if first click = ascending
  onChangeSort: PropTypes.func.isRequired, // func({ key, ascending }) => undefined
  children: PropTypes.node.isRequired
}

export default function WorkflowList (props) {
  const {
    className,
    workflows,
    onClickDeleteWorkflow = null,
    onClickDuplicateWorkflow = null,
    apiForShareModal = null,
    onWorkflowChanging = null,
    onWorkflowChanged = null
  } = props
  const [sort, setSort] = React.useState({ key: 'last_update', ascending: false })
  const showActions = onClickDeleteWorkflow && onClickDuplicateWorkflow && apiForShareModal && true
  const sortedWorkflows = React.useMemo(() => {
    const TextComparator = new Intl.Collator() // locale alphabetical
    const { key, ascending } = sort
    // workflow.last_update is ISO8601 Date. We can sort it lexicographically.
    const ret = workflows.slice().sort((a, b) => TextComparator.compare(a[key], b[key]))
    if (!ascending) {
      ret.reverse()
    }
    return ret
  }, [workflows, sort])

  return (
    <div className={`workflow-list ${className}`}>
      <table>
        <thead>
          <tr>
            <th className='title'>
              <SortableColumnName
                sort={sort}
                sortKey='name'
                defaultAscending
                onChangeSort={setSort}
              >
                <Trans id='js.Workflows.WorkflowList.title'>Title</Trans>
              </SortableColumnName>
            </th>
            <th className='owner'>
              <Trans id='js.Workflows.WorkflowList.owner'>Owner</Trans>
            </th>
            <th className='updated'>
              <SortableColumnName
                sort={sort}
                sortKey='last_update'
                defaultAscending={false}
                onChangeSort={setSort}
              >
                <Trans id='js.Workflows.WorkflowList.updated'>Updated</Trans>
              </SortableColumnName>
            </th>
            <th className='privacy'>
              <Trans id='js.Workflows.WorkflowList.privacy'>Privacy</Trans>
            </th>
            {showActions ? (
              <th className='actions' />
            ) : null}
          </tr>
        </thead>
        <tbody>
          {sortedWorkflows.map(workflow => (
            <Workflow
              key={workflow.id}
              workflow={workflow}
              onClickDeleteWorkflow={onClickDeleteWorkflow}
              onClickDuplicateWorkflow={onClickDuplicateWorkflow}
              apiForShareModal={apiForShareModal}
              onWorkflowChanging={onWorkflowChanging}
              onWorkflowChanged={onWorkflowChanged}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
WorkflowList.propTypes = {
  workflows: WorkflowListPropType.isRequired,
  className: PropTypes.string.isRequired,
  onClickDeleteWorkflow: PropTypes.func, // func(id) => undefined, or null if not allowed to delete
  onClickDuplicateWorkflow: PropTypes.func, // func(id) => undefined, or null if user must _open_ to duplicate
  apiForShareModal: PropTypes.shape({
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, canEdit) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublic: PropTypes.func.isRequired // func(id, isPublic) => Promise[null]
  }), // or null if user is not allowed to change sharing settings
  onWorkflowChanging: PropTypes.func, // func(id, { k: v, ...}) => undefined, or null if caller doesn't care
  onWorkflowChanged: PropTypes.func // func(id) => undefined, or null if caller doesn't care
}
