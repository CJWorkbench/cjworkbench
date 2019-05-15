import React from 'react'
import PropTypes from 'prop-types'
import Report from './Report'
import ShareCard from './ShareCard'

function EmptyReport () {
  return (
    <article className='report'>
      <p className='empty-report'>
        There are no charts in this Workflow. Add charts to tabs, and they'll appear here.
      </p>
    </article>
  )
}

export default function Dashboard ({ workflowId, tabs }) {

  return (
    <article className='report'>
      {tabs.length === 0 ? (
        <EmptyReport />
      ) : (
        <>
          <ShareCard workflowId={workflowId} />
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
