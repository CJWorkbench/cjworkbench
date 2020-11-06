import React from 'react'
import PropTypes from 'prop-types'
import StepList from './StepList'
import OutputPane from './OutputPane'
import PaneSelect from './PaneSelect'
import * as propTypes from './propTypes'
import Report from './Report'

/**
 * The Workflow editing interface.
 *
 * The interface has:
 *
 * * A <PaneSelect> -- panes for the user to choose. A pane is a Workflow tab
 *   or a report.
 * * The currently-selected pane.
 *
 * We pass the pane's ref to its children, so they can open up a Portal within
 * a pane. (This is for <AddData>: its modal must appear atop the pane but not
 * atop the <PaneSelect>.)
 */
const WorkflowEditor = React.memo(function WorkflowEditor ({ api, selectedPane, selectReportPane }) {
  const paneRef = React.useRef(null)

  return (
    <>
      <PaneSelect
        selectedPane={selectedPane}
        selectReportPane={selectReportPane}
      />

      {selectedPane.pane === 'tab' ? (
        <div className='workflow-columns' ref={paneRef}>
          <StepList api={api} paneRef={paneRef} />
          <OutputPane />
        </div>
      ) : (
        <Report />
      )}
    </>
  )
})
WorkflowEditor.propTypes = {
  api: PropTypes.object.isRequired,
  selectedPane: propTypes.selectedPane.isRequired,
  selectReportPane: PropTypes.func.isRequired // func() => undefined
}
export default WorkflowEditor
