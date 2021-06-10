import { useCallback, useState, useMemo } from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import Workflow from './Workflow'
import SortAscendingIcon from '../../icons/sort-ascending.svg'
import SortDescendingIcon from '../../icons/sort-descending.svg'
import NothingIcon from '../../icons/nothing.svg'

const WorkflowListPropType = PropTypes.arrayOf(
  PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    last_update: PropTypes.string.isRequired, // ISO8601 String
    public: PropTypes.bool.isRequired,
    secret_id: PropTypes.string.isRequired // maybe empty string
  }).isRequired
)
export { WorkflowListPropType }

function SortableColumnName (props) {
  const { sort, sortKey, defaultAscending, onChangeSort, children } = props

  const handleClickSort = useCallback(
    ev => {
      ev.preventDefault()
      const ascending = sort.key === sortKey ? !sort.ascending : defaultAscending
      onChangeSort({ key: sortKey, ascending })
    },
    [sort, sortKey, defaultAscending, onChangeSort]
  )

  return (
    <a href='#' onClick={handleClickSort}>
      {children}
      {sort.key === sortKey
        ? (sort.ascending ? <SortAscendingIcon /> : <SortDescendingIcon />)
        : <NothingIcon />}
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

function compareNumbers (a, b) {
  return a - b
}

function compareIso8601 (a, b) {
  return a < b
    ? -1
    : (b < a ? 1 : 0)
}

function privacyLevel (workflow) {
  if (workflow.public) {
    return 0
  }
  if (workflow.secret_id) {
    return 1
  }
  return 2
}

function comparePrivacy (a, b) {
  // least-private to most-private
  return privacyLevel(a) - privacyLevel(b)
}

function sortWorkflows (workflows, { key, ascending }) {
  const partialComparator = createPartialComparator(key)
  const fullComparator = (a, b) => partialComparator(a, b) || compareIso8601(a.last_update, b.last_update)
  const result = workflows.slice().sort(fullComparator)
  if (!ascending) {
    result.reverse()
  }
  return result
}

function createPartialComparator (sortKey) {
  switch (sortKey) {
    case 'fetchesPerDay': return (a, b) => compareNumbers(a.fetchesPerDay, b.fetchesPerDay)
    case 'last_update': return (a, b) => 0
    case 'privacy': return (a, b) => comparePrivacy(a, b)
    case 'name': {
      const collator = new Intl.Collator()
      return (a, b) => collator.compare(a.name, b.name)
    }
  }
}

export default function WorkflowList (props) {
  const {
    className,
    workflows,
    user = null,
    api = null,
    onWorkflowChanging = null,
    onWorkflowChanged = null,
    onWorkflowDuplicating = null,
    onWorkflowDuplicated = null
  } = props
  const [sort, setSort] = useState({ key: 'last_update', ascending: false })
  const showActions = Boolean(api)
  const sortedWorkflows = useMemo(() => sortWorkflows(workflows, sort), [workflows, sort])

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
            <th className='privacy'>
              <SortableColumnName
                sort={sort}
                sortKey='privacy'
                defaultAscending
                onChangeSort={setSort}
              >
                <Trans id='js.Workflows.WorkflowList.privacy'>Privacy</Trans>
              </SortableColumnName>
            </th>
            <th className='fetches-per-day'>
              <SortableColumnName
                sort={sort}
                sortKey='fetchesPerDay'
                defaultAscending={false}
                onChangeSort={setSort}
              >
                <Trans id='js.Workflows.WorkflowList.fetchesPerDay'>Auto updates</Trans>
              </SortableColumnName>
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
            {showActions ? <th className='actions' /> : null}
          </tr>
        </thead>
        <tbody>
          {sortedWorkflows.map(workflow => (
            <Workflow
              key={workflow.id}
              workflow={workflow}
              user={user}
              api={api}
              onWorkflowChanging={onWorkflowChanging}
              onWorkflowChanged={onWorkflowChanged}
              onWorkflowDuplicating={onWorkflowDuplicating}
              onWorkflowDuplicated={onWorkflowDuplicated}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
WorkflowList.propTypes = {
  workflows: WorkflowListPropType.isRequired,
  user: PropTypes.object, // or null
  className: PropTypes.string.isRequired,
  onClickDeleteWorkflow: PropTypes.func, // func(id) => undefined, or null if not allowed to delete
  onClickDuplicateWorkflow: PropTypes.func, // func(id) => undefined, or null if user must _open_ to duplicate
  api: PropTypes.shape({
    deleteWorkflow: PropTypes.func.isRequired, // func(id) => Promise[null]
    duplicateWorkflow: PropTypes.func.isRequired, // func(id) => Promise[{ id, name }]
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, role) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublicAccess: PropTypes.func.isRequired // func(id, isPublic, hasSecret) => Promise[{workflow}]
  }), // null if editing is not allowed
  onWorkflowChanging: PropTypes.func, // func(id, {k: v, ...}) => undefined, or null if no api
  onWorkflowChanged: PropTypes.func, // func(id, {k: v, ...}?) => undefined, or null if no api
  onWorkflowDuplicating: PropTypes.func, // func(id, {k: v, ...}) => undefined, or null if no api
  onWorkflowDuplicated: PropTypes.func // func(id) => undefined, or null if no api
}
