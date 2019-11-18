import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

function groupAutofetches (autofetches) {
  const groups = {} // workflow-id => { workflow, nFetchesPerDay, autofetches }
  for (const autofetch of autofetches) {
    const groupId = String(autofetch.workflow.id)
    if (!(groupId in groups)) {
      groups[groupId] = {
        workflow: autofetch.workflow,
        nFetchesPerDay: 0,
        autofetches: []
      }
    }
    const group = groups[groupId]
    group.nFetchesPerDay += 86400 / autofetch.wfModule.fetchInterval
    group.autofetches.push(autofetch)
  }

  return Object.values(groups).sort((a, b) => b.nFetchesPerDay - a.nFetchesPerDay || a.workflow.name.localeCompare(b.workflow.name))
}

const QuotaExceeded = React.memo(function QuotaExceeded ({ workflowId, wfModuleId, maxFetchesPerDay, nFetchesPerDay, autofetches }) {
  const autofetchGroups = groupAutofetches(autofetches)

  return (
    <div className='quota-exceeded'>
      <h5><Trans id='js.params.Custom.VersionSelect.QuotaExceeded.title' description='This must be all-caps for styling reasons'>AUTO-UPDATE QUOTA EXCEEDED</Trans></h5>
      <p>
        <Trans id='js.params.Custom.VersionSelect.QuotaExceeded.requestsVsLimit' description='The two tags add emphasis'>
            You're requesting {''}
          <strong className='n-fetches-per-day'>{Math.ceil(numberFormatter.format(nFetchesPerDay))}</strong> {''}
            updates per day across all your workflows. Your daily limit is {''}
          <strong className='max-fetches-per-day'>{numberFormatter.format(maxFetchesPerDay)}</strong>.
        </Trans>
      </p>
      <p>
        <Trans id='js.params.Custom.VersionSelect.QuotaExceeded.quotasteps'>
          Here are the steps that count against your limit.
          Adjust their update times or set them to manual, then click "Retry" above.
        </Trans>
      </p>
      <table>
        <thead>
          <tr>
            <th className='n-fetches-per-day'><Trans id='js.params.Custom.VersionSelect.QuotaExceeded.fetchesPerDay.heading'>#/day</Trans></th>
            <th className='step'><Trans id='js.params.Custom.VersionSelect.QuotaExceeded.workFlow.heading'>Workflow</Trans></th>
            <th className='open' />
          </tr>
        </thead>
        <tbody>
          {autofetchGroups.map(({ workflow, nFetchesPerDay, autofetches }) => (
            <tr key={workflow.id}>
              <td className='n-fetches-per-day'>
                {numberFormatter.format(nFetchesPerDay)}
              </td>
              <td className='workflow'>
                <div className='workflow'>
                  {workflowId === workflow.id ? (
                    <div className='this-workflow'>(<Trans id='js.params.Custom.VersionSelect.QuotaExceeded.thisWorkflow'>This workflow</Trans>)</div>
                  ) : (
                    <div className='other-workflow'>
                      {workflow.name}{' '}
                      <a className='edit' target='_blank' rel='noopener noreferrer' href={`/workflows/${workflow.id}/`}>
                        <Trans id='js.params.Custom.VersionSelect.QuotaExceeded.editWorkflow'>Edit workflow</Trans> <i className='icon-edit' />
                      </a>
                    </div>
                  )}
                </div>
                <ul className='steps'>
                  {autofetches.map(({ tab, wfModule }) => (
                    <li key={wfModule.id}>
                      {workflowId === workflow.id && wfModuleId === wfModule.id ? (
                        <>(<Trans id='js.params.Custom.VersionSelect.QuotaExceeded.thisStep.fetchesPerDay'>You asked for this step to make {numberFormatter.format(86400 / wfModule.fetchInterval)} updates per day.</Trans>)</>
                      ) : (
                        <Trans id='js.params.Custom.VersionSelect.QuotaExceeded.otherStep.fetchesPerDay' description='The {1} argument is a tab name'>Step {wfModule.order + 1} on {tab.name} makes {numberFormatter.format(86400 / wfModule.fetchInterval)} updates per day.</Trans>
                      )}
                    </li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className='request-lift'>
        <Trans id='js.params.Custom.VersionSelect.QuotaExceeded.requestLift' description='The tag is a mailto url'>
            Need a higher limit?
            Send us a short <a href='mailto:pierre@tablesdata.com' target='_blank' rel='noopener noreferrer'>email</a>.
        </Trans>
      </p>
    </div>
  )
})
QuotaExceeded.propTypes = {
  maxFetchesPerDay: PropTypes.number.isRequired,
  nFetchesPerDay: PropTypes.number.isRequired,
  autofetches: PropTypes.arrayOf(PropTypes.shape({
    workflow: PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired
    }).isRequired,
    tab: PropTypes.shape({
      name: PropTypes.string.isRequired
    }).isRequired,
    wfModule: PropTypes.shape({
      id: PropTypes.number.isRequired,
      fetchInterval: PropTypes.number.isRequired
    })
  }).isRequired).isRequired
}
export default QuotaExceeded
