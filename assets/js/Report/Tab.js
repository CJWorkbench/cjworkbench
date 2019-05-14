import React from 'react'
import PropTypes from 'prop-types'
import * as propTypes from './propTypes'
import WfModule from './WfModule'

const Tab = React.memo(function Tab ({ workflowId, isPublic, name, slug, wfModules }) {
  return (
    <section className='tab'>
      <h3>{name}</h3>
      {wfModules.map(wfm => (
        <WfModule
          key={wfm.id}
          workflowId={workflowId}
          isPublic={isPublic}
          {...wfm}
        />
      ))}
    </section>
  )
})
Tab.propTypes = {
  workflowId: PropTypes.number.isRequired,
  isPublic: PropTypes.bool.isRequired,
  ...propTypes.Tab
}
export default Tab
