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
    wfModuleStatus: PropTypes.oneOf(['ready', 'busy', 'error']).isRequired,
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
        visible={!!htmlOutput}
        wfModuleId={wfModuleId}
        workflowId={workflowId}
        isPublic={isPublic}
        lastRelevantDeltaId={lastRelevantDeltaId}
      />
    )
  }

  render () {
    const { wfModuleStatus } = this.props

    const className = 'outputpane module-' + wfModuleStatus

    return (
      <div className={className}>
        {this.renderOutputIFrame()}
        {this.renderTableView()}
      </div>
    )
  }
}

function mapStateToProps(state, ownProps) {
  const { workflow, wfModules, modules } = state
  const wfModuleId = workflow.wf_modules[state.selected_wf_module || 0] || null
  const wfModule = wfModules[String(wfModuleId)] || null
  const selectedModule = modules[String(wfModule ? wfModule.module_version.module : null)] || null
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
    lastRelevantDeltaId: wfModule ? wfModule.last_relevant_delta_id : null,
    wfModuleId,
    isPublic: workflow.public,
    isReadOnly: workflow.read_only,
    htmlOutput: wfModule ? wfModule.html_output : false,
    wfModuleStatus: wfModule ? wfModule.status : 'ready',
    showColumnLetter,
    sortColumn,
    sortDirection,
  }
}

export default connect(
  mapStateToProps
)(OutputPane)
