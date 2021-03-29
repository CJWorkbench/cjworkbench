import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import WorkflowList, { WorkflowListPropType } from './WorkflowList'

export default function WorkflowsSharedWithMeMain (props) {
  const { workflows, user = null } = props
  return (
    <main className='workflows'>
      <header>
        <h1>
          <Trans id='js.Workflows.WorkflowLists.nav.sharedWithMe'>
            Workflows shared with me
          </Trans>
        </h1>
      </header>
      {workflows.length === 0
        ? (
          <div className='placeholder'>
            <Trans id='js.Workflows.WorkflowLists.workflowsWillAppearHere'>
              Workflows shared with you as collaborator will appear here
            </Trans>
            ~ ༼ つ ◕_◕ ༽つ
          </div>
          )
        : <WorkflowList className='shared-with-me' workflows={workflows} user={user} />}
    </main>
  )
}
WorkflowsSharedWithMeMain.propTypes = {
  workflows: WorkflowListPropType.isRequired,
  user: PropTypes.object // or null
}
