import React from 'react'
import PropTypes from 'prop-types'
import { selectPaneAction } from './actions'
import ModuleStack from './ModuleStack'
import OutputPane from './OutputPane'
import PaneSelect from './PaneSelect'
import * as propTypes from './propTypes'
import Report from '../Report'

const WorkflowEditor = React.memo(function WorkflowEditor ({ api, selectedPane, selectReportPane }) {
  return (
    <>
      {selectedPane.pane === 'tab' ? (
        <div className='workflow-columns'>
          <ModuleStack api={api} />
          <OutputPane api={api} />
        </div>
      ) : (
        <Report />
      )}

      <PaneSelect
        selectedPane={selectedPane}
        selectReportPane={selectReportPane}
      />
    </>
  )
})
WorkflowEditor.propTypes = {
  api: PropTypes.object.isRequired,
  selectedPane: propTypes.selectedPane.isRequired,
  selectReportPane: PropTypes.func.isRequired // func() => undefined
}
export default WorkflowEditor
