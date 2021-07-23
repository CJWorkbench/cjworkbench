import { memo, useRef } from 'react'
import PropTypes from 'prop-types'
import StepList from './StepList'
import OutputPane from './OutputPane'
import PaneSelect from './PaneSelect'
import * as propTypes from './propTypes'
import Report from './Report'
import DatasetPublisher from './DatasetPublisher'

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
const WorkflowEditor = memo(function WorkflowEditor ({
  api,
  selectedPane,
  selectDatasetPublisherPane,
  selectReportEditorPane
}) {
  const paneRef = useRef(null)

  return (
    <>
      <PaneSelect
        selectedPane={selectedPane}
        selectDatasetPublisherPane={selectDatasetPublisherPane}
        selectReportEditorPane={selectReportEditorPane}
      />

      {selectedPane.pane === 'tab'
        ? (
          <div className='workflow-columns' ref={paneRef}>
            <StepList api={api} paneRef={paneRef} />
            <OutputPane />
          </div>
          )
        : null}
      {selectedPane.pane === 'report' ? <Report /> : null}
      {selectedPane.pane === 'dataset' ? <DatasetPublisher /> : null}
    </>
  )
})
WorkflowEditor.propTypes = {
  api: PropTypes.object.isRequired,
  selectedPane: propTypes.selectedPane.isRequired,
  selectDatasetPublisherPane: PropTypes.func.isRequired, // func() => undefined
  selectReportEditorPane: PropTypes.func.isRequired // func() => undefined
}
export default WorkflowEditor
