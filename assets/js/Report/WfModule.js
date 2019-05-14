import React from 'react'
import PropTypes from 'prop-types'
import propTypes from 'prop-types'
import OutputIframe from '../OutputIframe'

const WfModule = React.memo(function WfModule ({ workflowId, isPublic, id, deltaId }) {
  // Assume the chart itself has a title -- no need to write a title here.
  //
  // But we'll link back to the Workflow, so users can edit a chart.
  return (
    <figure>
      <OutputIframe
        visible
        workflowId={workflowId}
        isPublic={isPublic}
        wfModuleId={id}
        deltaId={deltaId}
      />
      <figcaption>
        <a href='#' onClick={/*navigateToWfModule*/null}>Jump to Workflow</a>
      </figcaption>
    </figure>
  )
})
WfModule.propTypes = {
  workflowId: PropTypes.number.isRequired,
  isPublic: PropTypes.bool.isRequired,
  ...propTypes.WfModule
}
export default WfModule
