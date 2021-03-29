import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import WorkflowList, { WorkflowListPropType } from './WorkflowList'

export default function ExampleWorkflowsMain (props) {
  const { workflows, user } = props
  return (
    <main className='workflows'>
      <header>
        <h1>
          <Trans id='js.Workflows.WorkflowLists.nav.recipes'>
            Community workflows
          </Trans>
        </h1>
      </header>
      {workflows.length === 0
        ? (
          <div className='placeholder'>
            <Trans id='js.Workflows.WorkflowLists.publishNewRecipes'>
              Publish workflows as examples using Django admin
            </Trans>
          </div>
          )
        : <WorkflowList className='example' workflows={workflows} user={user} />}
    </main>
  )
}
ExampleWorkflowsMain.propTypes = {
  workflows: WorkflowListPropType.isRequired,
  user: PropTypes.object // or null
}
