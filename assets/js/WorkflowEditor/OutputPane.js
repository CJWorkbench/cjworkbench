// Display of output from currently selected module

import React from 'react'
import PropTypes from 'prop-types'
import DelayedTableSwitcher from '../table/DelayedTableSwitcher'
import OutputIframe from '../OutputIframe'
import { connect } from 'react-redux'
import { withI18n } from '@lingui/react'
import { t } from '@lingui/macro'

export class OutputPane extends React.Component {
  static propTypes = {
    loadRows: PropTypes.func.isRequired, // func(wfModuleId, deltaId, startRowInclusive, endRowExclusive) => Promise[Array[Object] or error]
    workflowId: PropTypes.number.isRequired,
    wfModuleBeforeError: PropTypes.shape({
      id: PropTypes.number.isRequired,
      deltaId: PropTypes.number, // or null -- it may not be rendered
      status: PropTypes.oneOf(['ok', 'busy', 'unreachable']).isRequired, // can't be 'error'
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
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    })
  }

  /**
   * Return the WfModule we want to render for the user.
   *
   * This will _never_ be an "error"-status WfModule. If there's an error, we
   * want the user to see the input. (This component will also render a notice
   * saying it's showing the input.)
   */
  get wfModuleForTable () {
    const { wfModuleBeforeError, wfModule } = this.props

    if (wfModuleBeforeError) {
      // We're focused on an error module. The user wants to see its _input_ to
      // debug it.
      return wfModuleBeforeError
    } else if (wfModule && wfModule.status !== 'error') {
      return wfModule
    } else {
      // Either there's no selected WfModule, or the selected WfModule has
      // status === 'error' and it's the first in the tab. Either way, we want
      // to render a "placeholder" table.
      return null
    }
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
          {this.props.i18n._(t('js.WorkflowEditor.OutputPane.showingInput.becauseError')`This was the data that led to an error. Please correct the error in the left pane.`)}
        </p>
      )
    } else {
      return null
    }
  }

  render () {
    const { isReadOnly, loadRows, wfModule } = this.props
    const wfm = this.wfModuleForTable
    const className = 'outputpane module-' + (wfModule ? wfModule.status : 'unreachable')

    return (
      <div className={className}>
        {this.renderOutputIFrame()}
        {this.renderShowingInput()}
        <DelayedTableSwitcher
          key='table'
          wfModuleId={wfm ? wfm.id : null}
          status={wfm ? wfm.status : null}
          deltaId={wfm ? wfm.deltaId : null}
          columns={wfm ? wfm.columns : null}
          nRows={wfm ? wfm.nRows : null}
          isReadOnly={isReadOnly}
          loadRows={loadRows}
        />
      </div>
    )
  }
}

function wfModuleStatus (wfModule) {
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

function mapStateToProps (state) {
  const { workflow, wfModules, tabs } = state
  const tabSlug = workflow.tab_slugs[workflow.selected_tab_position]
  const tab = tabs[tabSlug]
  const wfModuleArray = tab.wf_module_ids.map(id => wfModules[String(id)])

  const wfModuleIndex = tab.selected_wf_module_position
  let wfModule = wfModuleArray[wfModuleIndex] || null
  let wfModuleBeforeError

  const status = wfModule ? wfModuleStatus(wfModule) : 'busy'

  if (wfModule === null && tab.wf_module_ids[wfModuleIndex]) {
    // We're pointing at a "placeholder" module: its id isn't in wfModules.
    // HACK: for now, we want OutputPane to render something different (it needs
    // to give TableSwitcher a "busy"-status WfModule).
    wfModule = {
      id: -1,
      html_output: false,
      status: 'busy',
      cached_render_result_delta_id: null,
      columns: null,
      nRows: null
    }
  }

  // If we're pointing at a module that output an error, we'll want to display
  // its _input_ (the previous module's output) to help the user fix things.
  if (status === 'error' && tab.selected_wf_module_position > 0) {
    const lastGood = wfModuleArray[wfModuleIndex - 1]
    wfModuleBeforeError = {
      id: lastGood.id,
      deltaId: lastGood.cached_render_result_delta_id,
      status: wfModuleStatus(lastGood),
      columns: lastGood.output_columns,
      nRows: lastGood.output_n_rows
    }
  }

  return {
    workflowId: workflow.id,
    wfModule: wfModule ? {
      id: wfModule.id,
      htmlOutput: wfModule.html_output,
      status,
      deltaId: wfModule.cached_render_result_delta_id,
      columns: wfModule.output_columns,
      nRows: wfModule.output_n_rows
    } : null,
    wfModuleBeforeError,
    isPublic: workflow.public,
    isReadOnly: workflow.read_only
  }
}

function mapDispatchToProps (dispatch) {
  return {
    loadRows: (wfModuleId, deltaId, startRow, endRow) => {
      return dispatch((_, __, api) => {
        return api.render(wfModuleId, startRow, endRow) // ignore deltaId -- for now
      })
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(withI18n()(OutputPane))
