import React from 'react'
import PropTypes from 'prop-types'
import Report from './Report'
import ShareCard from './ShareCard'
import { Trans } from '@lingui/macro'

function EmptyReport () {
  return (
    <article className='report'>
      <p className='empty-report'>
        <Trans id='js.Report.Dashboard.addChartstoTabs'>Add charts to tabs, and they'll appear here.</Trans>
      </p>
    </article>
  )
}

export default function Dashboard ({ workflowId, isPublic, tabs }) {
  return (
    <article className='report'>
      {tabs.length === 0 ? (
        <EmptyReport />
      ) : (
        <>
          <ShareCard workflowId={workflowId} isPublic={isPublic} />
          <Report workflowId={workflowId} />
        </>
      )}
    </article>
  )
}
Dashboard.propTypes = {
  workflowId: PropTypes.number.isRequired,
  isPublic: PropTypes.bool.isRequired,
  tabs: PropTypes.array.isRequired // empty if no tabs have iframes
}
