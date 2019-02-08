// Display of output from currently selected module

import React from 'react'
import PropTypes from 'prop-types'
import TableSwitcher from './table/TableSwitcher'
import OutputIframe from './OutputIframe'
import { connect } from 'react-redux'

export class OutputPane extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    workflowId: PropTypes.number.isRequired,
    wfModuleBeforeError: PropTypes.shape({
      id: PropTypes.number.isRequired,
      deltaId: PropTypes.number, // or null -- it may not be rendered
      columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      }).isRequired), // or null
      nRows: PropTypes.number // or null
    }), // or null if no error
    wfModule: PropTypes.shape({
      id: PropTypes.number.isRequired,
      htmlOutput: PropTypes.bool.isRequired,
      status: PropTypes.oneOf(['ok', 'busy', 'error', 'unreachable']).isRequired,
      deltaId: PropTypes.number, // or null if not yet rendered
      columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      }).isRequired), // or null
      nRows: PropTypes.number // or null
    }), // or null if no selection
    isPublic: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    showColumnLetter: PropTypes.bool.isRequired
  }

  renderTable() {
    const { api, isReadOnly, showColumnLetter, wfModuleBeforeError, wfModule } = this.props

    let wfm
    let wfModuleId
    if (wfModuleBeforeError) {
      wfm = wfModuleBeforeError
      wfModuleId = wfModuleBeforeError.id
    } else if (wfModule && wfModule.status === 'ok') {
      wfm = wfModule
      wfModuleId = wfm.id
    } else {
      // We're focused on a module that is not ok. It is one of:
      // * 'busy': no results to show (we want to see the previous table, whatever it is)
      // * 'unreachable': no results to show (we want to see the previous table, whatever it is)
      // * 'error': no results to show (assuming wfModuleBeforeError is set, we want to see the previous table)
      //
      // "see the previous table" is TableSwitcher's domain. Our job is to tell
      // TableSwitcher we don't want to render this wfModule's data.
      wfm = null
      // TableSwitcher clears the table when you switch WfModules. (Otherwise
      // it shows the last-good table.) We want the last-good table here, so
      // we should pass wfModuleId even though we don't want to render the table
      wfModuleId = wfModule ? wfModule.id : null
    }

    // Make a table component even if no module ID (should still show an empty table)
    return (
      <TableSwitcher
        key='table'
        wfModuleId={wfModuleId}
        deltaId={wfm ? wfm.deltaId : null}
        columns={wfm ? wfm.columns : null}
        nRows={wfm ? wfm.nRows : null}
        api={api}
        isReadOnly={isReadOnly}
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
        {status === 'busy' ? (
          <div key='spinner' className="spinner-container-transparent">
            <div className="spinner-l1">
              <div className="spinner-l2">
                <div className="spinner-l3"></div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    )
  }
}

function wfModuleStatus(wfModule) {
  // TODO don't copy/paste from OutputPane.js
  if (wfModule.nClientRequests > 0) {
    // When we've just sent an HTTP request and not received a response,
    // mark ourselves "busy". This is great for when the user clicks "fetch"
    // and then is waiting for the server to set the status.
    //
    // The state stores server data separately than client data, so there's
    // no race when setting status and so if the "fetch" does nothing and the
    // server doesn't change wfModule.status, the client still resets its
    // perceived status.
    return 'busy'
  } else if (wfModule.is_busy) {
    return 'busy'
  } else if (!wfModule.output_status) {
    // placeholder? TODO verify this can actually happen
    return 'busy'
  } else {
    return wfModule.output_status
  }
}

function mapStateToProps(state, ownProps) {
  const { workflow, wfModules, tabs, modules } = state
  const tabSlug = workflow.tab_slugs[workflow.selected_tab_position]
  const tab = tabs[tabSlug]
  const wfModuleArray = tab.wf_module_ids.map(id => wfModules[String(id)])

  let wfModuleIndex = tab.selected_wf_module_position
  let wfModule = wfModuleArray[wfModuleIndex] || null
  let wfModuleBeforeError

  const status = wfModule ? wfModuleStatus(wfModule) : 'busy'

  // If we're pointing at a module that output an error, we'll want to display
  // its _input_ (the previous module's output) to help the user fix things.
  if (status === 'error' && tab.selected_wf_module_position > 0) {
    const lastGood = wfModuleArray[wfModuleIndex - 1]
    wfModuleBeforeError = {
      id: lastGood.id,
      deltaId: lastGood.cached_render_result_delta_id,
      columns: lastGood.output_columns,
      nRows: lastGood.output_n_rows
    }
  }

  const selectedModule = (wfModule ? modules[wfModule.module] : null) || null
  const id_name = selectedModule ? selectedModule.id_name : null

  const showColumnLetter = id_name === 'formula' || id_name === 'reordercolumns'

  return {
    workflowId: workflow.id,
    wfModule: wfModule ? {
      id: wfModule.id,
      module: wfModule.module,
      htmlOutput: wfModule.html_output,
      status,
      deltaId: wfModule.cached_render_result_delta_id,
      columns: wfModule.output_columns,
      nRows: wfModule.output_n_rows
    } : null,
    wfModuleBeforeError: wfModuleBeforeError,
    isPublic: workflow.public,
    isReadOnly: workflow.read_only,
    showColumnLetter
  }
}

export default connect(
  mapStateToProps
)(OutputPane)
