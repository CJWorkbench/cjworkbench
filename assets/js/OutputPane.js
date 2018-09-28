// Display of output from currently selected module

import React from 'react'
import PropTypes from 'prop-types'
import TableView from './table/TableView'
import OutputIframe from './OutputIframe'
import debounce from 'debounce'
import { connect } from 'react-redux'
import { findParamValByIdName} from './utils'
import { sortDirectionNone } from './table/UpdateTableAction'

export class OutputPane extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    workflowId: PropTypes.number.isRequired,
    lastRelevantDeltaId: PropTypes.number.isRequired,
    wfModuleId: PropTypes.number,
    wfModuleStatus: PropTypes.oneOf(['ok', 'busy', 'waiting', 'error', 'unreachable']).isRequired,
    isInputBecauseOutputIsError: PropTypes.bool.isRequired,
    isPublic: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    showColumnLetter: PropTypes.bool.isRequired,
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number,
    htmlOutput: PropTypes.bool
  }

  renderTableView () {
    const { wfModuleId, lastRelevantDeltaId, api, isReadOnly, sortColumn, sortDirection, showColumnLetter } = this.props

    // Make a table component even if no module ID (should still show an empty table)
    return (
      <TableView
        key='table'
        wfModuleId={wfModuleId}
        lastRelevantDeltaId={lastRelevantDeltaId}
        api={api}
        isReadOnly={isReadOnly}
        sortColumn={sortColumn}
        sortDirection={sortDirection}
        showColumnLetter={showColumnLetter}
      />
    )
  }

  renderOutputIFrame () {
    const { htmlOutput, wfModuleId, workflowId, isPublic, lastRelevantDeltaId } = this.props

    // This iframe holds the module HTML output, e.g. a visualization.
    // We leave the component around even when there is no HTML because of
    // our solution to https://www.pivotaltracker.com/story/show/159637930:
    // DataGrid.js doesn't notice the resize that occurs when the iframe
    // appears or disappears.
    return (
      <OutputIframe
        key='iframe'
        visible={!!htmlOutput}
        wfModuleId={wfModuleId}
        workflowId={workflowId}
        isPublic={isPublic}
        lastRelevantDeltaId={lastRelevantDeltaId}
      />
    )
  }

  renderShowingInput () {
    if (this.props.isInputBecauseOutputIsError) {
      return (
        <p
          key='error'
          className='showing-input-because-error'
        >
          This was the data that led to an error. Please correct the error in the left pane.
        </p>
      )
    } else {
      return null
    }
  }

  render () {
    const { wfModuleStatus } = this.props

    const className = 'outputpane module-' + wfModuleStatus

    return (
      <div className={className}>
        {this.renderShowingInput()}
        {this.renderOutputIFrame()}
        {this.renderTableView()}
      </div>
    )
  }
}

const NullWfModule = {
  id: null,
  last_relevant_delta_id: null,
  html_output: false,
  status: 'unreachable',
}

function mapStateToProps(state, ownProps) {
  const { workflow, wfModules, modules } = state

  const selectedWfModule = wfModules[String(workflow.wf_modules[state.selected_wf_module])] || null

  let wfModule
  let isInputBecauseOutputIsError = false
  if (!selectedWfModule) {
    wfModule = NullWfModule
  } else if (selectedWfModule.status === 'error' || selectedWfModule.status === 'unreachable') {
    // Show the first WfModule _before_ this one.
    wfModule = workflow.wf_modules.slice(0, state.selected_wf_module)
      .reverse()
      .map(id => wfModules[id])
      .find(wfm => wfm.status === 'ok')

    if (wfModule) {
      isInputBecauseOutputIsError = true
    } else {
      wfModule = NullWfModule
    }
  } else {
    wfModule = selectedWfModule
  }

  const selectedModule = modules[String(selectedWfModule ? selectedWfModule.module_version.module : null)] || null
  const id_name = selectedModule ? selectedModule.id_name : null

  const showColumnLetter = id_name === 'formula' || id_name === 'reorder-columns'

  let sortColumn = null
  let sortDirection = sortDirectionNone

  if (id_name === 'sort-from-table') {
    const columnParam = findParamValByIdName(wfModule, 'column');
    const directionParam = findParamValByIdName(wfModule, 'direction').value;

    sortColumn = columnParam && columnParam.value || null
    sortDirection = directionParam || sortDirectionNone
  }

  return {
    workflowId: workflow.id,
    wfModuleId: wfModule.id,
    lastRelevantDeltaId: wfModule.last_relevant_delta_id,
    wfModuleStatus: wfModule.status,
    isInputBecauseOutputIsError,
    isPublic: workflow.public,
    isReadOnly: workflow.read_only,
    htmlOutput: wfModule.html_output,
    showColumnLetter,
    sortColumn,
    sortDirection,
  }
}

export default connect(
  mapStateToProps
)(OutputPane)
