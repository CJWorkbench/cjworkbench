import PropTypes from 'prop-types'
import { Page, MainNav } from '../Page'
import { WorkflowListPropType } from './WorkflowList'
import OwnedWorkflowsMain from './OwnedWorkflowsMain'
import WorkflowsSharedWithMeMain from './WorkflowsSharedWithMeMain'
import ExampleWorkflowsMain from './ExampleWorkflowsMain'

export default function Workflows (props) {
  const { api, currentPath, user, workflows } = props

  return (
    <Page>
      <MainNav user={user} currentPath={currentPath} />
      {currentPath === '/workflows'
        ? <OwnedWorkflowsMain workflows={workflows} user={user} api={api} />
        : null}
      {currentPath === '/workflows/shared-with-me'
        ? <WorkflowsSharedWithMeMain workflows={workflows} user={user} api={api} />
        : null}
      {currentPath === '/workflows/examples'
        ? <ExampleWorkflowsMain workflows={workflows} user={user} api={api} />
        : null}
    </Page>
  )
}
Workflows.propTypes = {
  api: PropTypes.shape({
    deleteWorkflow: PropTypes.func.isRequired, // func(id) => Promise[null]
    duplicateWorkflow: PropTypes.func.isRequired, // func(id) => Promise[{ id, name }]
    updateAclEntry: PropTypes.func.isRequired, // func(id, email, role) => Promise[null]
    deleteAclEntry: PropTypes.func.isRequired, // func(id, email) => Promise[null]
    setWorkflowPublic: PropTypes.func.isRequired // func(id, isPublic) => Promise[null]
  }).isRequired,
  workflows: WorkflowListPropType.isRequired,
  user: PropTypes.object, // null/undefined if logged out
  currentPath: PropTypes.string.isRequired
}
