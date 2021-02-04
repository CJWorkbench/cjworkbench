import React from 'react'
import { Trans } from '@lingui/macro'
import WorkflowList, { WorkflowListPropType } from './WorkflowList'

export default function WorkflowsSharedWithMeMain (props) {
  const { workflows } = props
  return (
    <main>
      <header>
        <h1><Trans id='js.Workflows.WorkflowLists.nav.sharedWithMe'>Workflows shared with me</Trans></h1>
      </header>
      {workflows.length === 0 ? (
        <div className='placeholder'>
          <Trans id='js.Workflows.WorkflowLists.workflowsWillAppearHere'>Workflows shared with you as collaborator will appear here</Trans>
          {''} ~ ༼ つ ◕_◕ ༽つ
        </div>
      ) : (
        <WorkflowList className='shared-with-me' workflows={workflows} />
      )}
    </main>
  )
}
WorkflowsSharedWithMeMain.propTypes = {
  workflows: WorkflowListPropType.isRequired
}
