// Display of output from currently selected module

import React from 'react'
import PropTypes from 'prop-types'
import TableSwitcher from './table/TableSwitcher'
import OutputIframe from './OutputIframe'
import debounce from 'debounce'
import { connect } from 'react-redux'
import { findParamValByIdName} from './utils'
import { sortDirectionNone } from './table/UpdateTableAction'

export class OutputPane extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    workflowId: PropTypes.number.isRequired,
    wfModuleBeforeError: PropTypes.shape({
      id: PropTypes.number.isRequired,
      deltaId: PropTypes.number.isRequired,
      columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      }).isRequired), // or null
      nRows: PropTypes.number // or null
    }), // or null if no error
    wfModule: PropTypes.shape({
      id: PropTypes.number.isRequired,
      htmlOutput: PropTypes.bool.isRequired,
      status: PropTypes.oneOf(['ok', 'busy', 'waiting', 'error', 'unreachable']).isRequired,
      deltaId: PropTypes.number, // or null if not yet rendered
      columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      }).isRequired), // or null
      nRows: PropTypes.number // or null
    }), // or null if no selection
    isPublic: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    showColumnLetter: PropTypes.bool.isRequired,
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number
  }

  renderTable() {
    const { api, isReadOnly, sortColumn, sortDirection, showColumnLetter, wfModuleBeforeError, wfModule } = this.props

    const wfm = wfModuleBeforeError ? wfModuleBeforeError : wfModule // may be null

    // Make a table component even if no module ID (should still show an empty table)
    return (
      <TableSwitcher
        key='table'
        wfModuleId={wfm ? wfm.id : null}
        deltaId={wfm ? wfm.deltaId : null}
        columns={wfm ? wfm.columns : null}
        nRows={wfm ? wfm.nRows : null}
        api={api}
        isReadOnly={isReadOnly}
        sortColumn={sortColumn}
        sortDirection={sortDirection}
        showColumnLetter={showColumnLetter}
      />
    )
  }

  renderOutputIFrame () {
    // Always show _this_ module's iframe. If this module has status 'error'
    // and it's the Python console, the iframe contains the stack trace. If
    // we showed the _input_ module's iframe we wouldn't render the stack
    // trace.

    const { wfModule, workflowId, isPublic } = this.props

    const wfModuleId = wfModule ? wfModule.id : null
    const deltaId = wfModule ? wfModule.deltaId : null
    const htmlOutput = wfModule ? wfModule.htmlOutput : false

    // This iframe holds the module HTML output, e.g. a visualization.
    // We leave the component around even when there is no HTML because of
    // our solution to https://www.pivotaltracker.com/story/show/159637930:
    // DataGrid.js doesn't notice the resize that occurs when the iframe
    // appears or disappears.
    return (
      <OutputIframe
        key='iframe'
        visible={htmlOutput}
        workflowId={workflowId}
        isPublic={isPublic}
        wfModuleId={wfModuleId}
        deltaId={deltaId}
      />
    )
  }

  renderShowingInput () {
    if (this.props.wfModuleBeforeError) {
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
    const { wfModule } = this.props
    const status = wfModule ? wfModule.status : 'unreachable'

    const className = 'outputpane module-' + status

    return (
      <div className={className}>
        {this.renderOutputIFrame()}
        {this.renderShowingInput()}
        {this.renderTable()}
      </div>
    )
  }
}

function mapStateToProps(state, ownProps) {
  const { workflow, wfModules, modules } = state

  let wfModule = wfModules[String(workflow.wf_modules[state.selected_wf_module])] || null
  let wfModuleBeforeError

  if (wfModule && (wfModule.status === 'error' || wfModule.status === 'unreachable')) {
    const errorIndex = workflow.wf_modules
      .findIndex(id => wfModules[String(id)].status === 'error')

    if (errorIndex > 0) {
      const lastGood = wfModules[String(workflow.wf_modules[errorIndex - 1])]
      wfModuleBeforeError = {
        id: lastGood.id,
        deltaId: lastGood.cached_render_result_delta_id,
        columns: lastGood.output_columns,
        nRows: lastGood.output_n_rows
      }
    }
  }

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
    wfModule: wfModule ? {
      id: wfModule.id,
      htmlOutput: wfModule.html_output,
      status: wfModule.status,
      deltaId: wfModule.cached_render_result_delta_id,
      columns: wfModule.output_columns,
      nRows: wfModule.output_n_rows
    } : null,
    wfModuleBeforeError: wfModuleBeforeError,
    isPublic: workflow.public,
    isReadOnly: workflow.read_only,
    showColumnLetter,
    sortColumn,
    sortDirection,
  }
}

export default connect(
  mapStateToProps
)(OutputPane)
