import React from 'react'
import PropTypes from 'prop-types'
import * as propTypes from './propTypes'
import Tab from './Tab'

function EmptyReport () {
  return (
    <article className='report'>
      <p className='empty-report'>
        There are no charts in this Workflow. Add charts to tabs, and they'll appear here.
      </p>
    </article>
  )
}


const Report = React.memo(function Report ({ workflowId, isPublic, tabs }) {
  if (!tabs.length) {
    return <EmptyReport />
  }

  return (
    <article className='report'>
      <h2>Charts</h2>
      {tabs.map(tab => (
        <Tab
          key={tab.slug}
          workflowId={workflowId}
          isPublic={isPublic}
          {...tab}
        />
      ))}
    </article>
  )
})
Report.propTypes = {
  workflowId: PropTypes.number.isRequired,
  isPublic: PropTypes.bool.isRequired,
  tabs: PropTypes.arrayOf(propTypes.Tab.isRequired).isRequired // may be empty
}
export default Report
