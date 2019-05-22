// UI for a single module within a workflow

import React from 'react'
import DataVersionModal from '../DataVersionModal'
import ErrorBoundary from '../../ErrorBoundary'
import WfModuleContextMenu from './WfModuleContextMenu'
import ParamsForm from '../../params/ParamsForm'
import EditableNotes from '../../EditableNotes'
import DeprecationNotice from './DeprecationNotice'
import StatusLine from './StatusLine'
import {
  clearNotificationsAction,
  startCreateSecretAction,
  deleteSecretAction,
  maybeRequestWfModuleFetchAction,
  quickFixAction,
  setSelectedWfModuleAction,
  setWfModuleParamsAction,
  setWfModuleCollapsedAction,
  setWfModuleNotesAction
} from '../../workflow-reducer'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import lessonSelector from '../../lessons/lessonSelector'
import { createSelector } from 'reselect'

const numberFormat = new Intl.NumberFormat()

// ---- WfModule ----
export class WfModule extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    isZenMode: PropTypes.bool.isRequired,
    isZenModeAllowed: PropTypes.bool.isRequired,
    module: PropTypes.shape({
      id_name: PropTypes.string.isRequired,
      help_url: PropTypes.string.isRequired,
      deprecated: PropTypes.shape({
        message: PropTypes.string.isRequired,
      }), // undefined by default
      name: PropTypes.string.isRequired,
      icon: PropTypes.string.isRequired,
      param_fields: PropTypes.arrayOf(PropTypes.shape({
        idName: PropTypes.string.isRequired,
        type: PropTypes.string.isRequired,
        items: PropTypes.string, // "option0|option1|option2", null except when type=menu/radio
        multiline: PropTypes.bool, // required for String
        placeholder: PropTypes.string, // required for many
        visibleIf: PropTypes.object // JSON spec or null
      }).isRequired).isRequired
    }), // or null for no module
    index: PropTypes.number.isRequired,
    wfModule: PropTypes.shape({
      params: PropTypes.object.isRequired,
    }), // null if loading
    inputWfModule: PropTypes.shape({
      id: PropTypes.number.isRequired,
      last_relevant_delta_id: PropTypes.number,
      cached_render_result_delta_id: PropTypes.number, // or null
      output_columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      })) // or null
    }), // or null
    isSelected: PropTypes.bool.isRequired,
    isAfterSelected: PropTypes.bool.isRequired,
    setWfModuleParams: PropTypes.func, // func(wfModuleId, { paramidname: newVal }) => undefined
    removeModule: PropTypes.func,
    api: PropTypes.object.isRequired,
    onDragStart: PropTypes.func, // func({ type:'WfModule',id,index }) => undefined; null if not draggable
    onDragEnd: PropTypes.func, // func() => undefined
    isLessonHighlight: PropTypes.bool.isRequired,
    isLessonHighlightNotes: PropTypes.bool.isRequired,
    isLessonHighlightCollapse: PropTypes.bool.isRequired,
    fetchModuleExists: PropTypes.bool.isRequired, // there is a fetch module anywhere in the workflow
    clearNotifications: PropTypes.func.isRequired, // func() => undefined
    maybeRequestFetch: PropTypes.func.isRequired, // func(wfModuleId) => undefined
    setSelectedWfModule: PropTypes.func.isRequired, // func(wfModuleId) => undefined
    setWfModuleCollapsed: PropTypes.func.isRequired, // func(wfModuleId, isCollapsed, isReadOnly) => undefined
    setZenMode: PropTypes.func.isRequired, // func(wfModuleId, bool) => undefined
    applyQuickFix: PropTypes.func.isRequired, // func(wfModuleId, action, args) => undefined
    setWfModuleNotes: PropTypes.func.isRequired // func(wfModuleId, notes) => undefined
  }

  notesInputRef = React.createRef()

  state = {
    editedNotes: null, // when non-null, input is focused
    isDataVersionModalOpen: false,
    isDragging: false,
    edits: {} // idName => newValue
  }

  get hasFetch () {
    return this.props.fields.some(f => f.type === 'custom' && (f.idName === 'version_select' || f.idName === 'version_select_simpler'))
  }

  get isEditing () {
    return Object.keys(this.state.edits).length > 0
  }

  onClickNotification = () => {
    this.props.clearNotifications(this.props.wfModule.id)

    this.setState({
      isDataVersionModalOpen: true
    })
  }

  // We become the selected module on any click
  onMouseDown = () => {
    if (!this.props.isSelected) {
      this.props.setSelectedWfModule(this.props.wfModule.id)
    }
  }

  startCreateSecret = (paramIdName) => {
    const { startCreateSecret, wfModule } = this.props
    return startCreateSecret(wfModule.id, paramIdName)
  }

  deleteSecret = (paramIdName) => {
    const { deleteSecret, wfModule } = this.props
    return deleteSecret(wfModule.id, paramIdName)
  }

  onDragStart = (ev) => {
    const dragObject = {
      type: 'WfModule',
      index: this.props.index,
      id: this.props.wfModule.id
    }
    ev.dataTransfer.setData('application/json', JSON.stringify(dragObject))
    ev.dataTransfer.effectAllowed = 'move'
    ev.dataTransfer.dropEffect = 'move'
    this.props.onDragStart(dragObject)

    this.setState({
      isDragging: true
    })
  }

  onDragEnd = (ev) => {
    this.props.onDragEnd()

    this.setState({
      isDragging: false
    })
  }

  getParameterValue (idName) {
    const fromState = this.state.edits[idName]
    const fromProps = this.props.wfModule ? this.props.wfModule.params[idName] : null

    return fromState === undefined ? fromProps : fromState
  }

  // Allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  getParamText = (paramIdName) => {
    return this.getParameterValue(paramIdName)
  }

  removeModule = () => {
    this.props.removeModule(this.props.wfModule.id)
  }

  // Optimistically updates the state, and then sends the new state to the server,
  // where it's persisted across sessions and through time.
  setCollapsed (isCollapsed) {
    this.props.setWfModuleCollapsed(this.props.wfModule.id, isCollapsed, this.props.isReadOnly)
  }

  collapse = () => {
    this.setCollapsed(true)
  }

  expand = () => {
    this.setCollapsed(false)
  }

  // when Notes icon is clicked, show notes and start in editable state if not read-only
  focusNote = () => {
    const ref = this.notesInputRef.current
    if (ref) { // only if not read-only
      ref.focus() // calls this.onFocusNote()
    }
  }

  onChangeNote = (ev) => {
    this.setState({ editedNotes: ev.target.value })
  }

  onFocusNote = () => {
    if (this.state.editedNotes === null) {
      this.setState({ editedNotes: this.props.wfModule.notes || '' })
    }
  }

  onBlurNote = () => {
    // Blur may come _immediately_ after cancel -- and before cancel's
    // setState() is processed. Use the callback approach to setState() to
    // make sure we're reading the value written by onCancelNote()
    this.setState((state, props) => {
      if (state.editedNotes === null) {
        // we canceled
      } else {
        props.setWfModuleNotes(props.wfModule.id, state.editedNotes)
      }
      return { editedNotes: null }
    })
  }

  onCancelNote = () => {
    this.setState({ editedNotes: null })
  }

  onCloseDataVersionModal = () => {
    this.setState({
      isDataVersionModalOpen: false
    })
  }

  applyQuickFix = (...args) => {
    this.props.applyQuickFix(this.props.wfModule.id, ...args)
  }

  onChangeIsZenMode = (ev) => {
    this.props.setZenMode(this.props.wfModule.id, ev.target.checked)
  }

  renderZenModeButton () {
    const { wfModule, module, isZenMode, isZenModeAllowed } = this.props

    if (!isZenModeAllowed) return null

    const className = `toggle-zen-mode ${isZenMode ? 'is-zen-mode' : 'not-zen-mode'}`
    const title = isZenMode ? 'exit Zen mode' : 'enter Zen mode'

    return (
      <label className={className} title={title}>
        <input type='checkbox' name='zen-mode' checked={isZenMode} onChange={this.onChangeIsZenMode} />
        <i className='icon-full-screen' />
      </label>
    )
  }

  onChange = (edits) => {
    this.setState({ edits })
  }

  onSubmit = () => {
    const { wfModule, setWfModuleParams, maybeRequestFetch } = this.props
    const { edits } = this.state

    // We sometimes call onSubmit() _immediately_ after onChange(). onChange()
    // sets this.state.edits, and then onSubmit() should submit them. To make
    // that happen, we need to use the callback version of setState().
    // (this.state.edits is the pre-onChange() data.)
    this.setState(({ edits }) => {
      if (Object.keys(edits).length > 0) {
        setWfModuleParams(wfModule.id, edits)
      }

      maybeRequestFetch(wfModule.id)

      return { edits: {} }
    })
  }

  get wfModuleStatus () {
    // TODO don't copy/paste from OutputPane.js
    const { wfModule } = this.props
    if (!wfModule) {
      return null
    } else if (wfModule.nClientRequests > 0) {
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

  render () {
    const { isReadOnly, index, wfModule, module, inputWfModule, tabs, currentTab } = this.props
    const { edits } = this.state

    const moduleSlug = module ? module.id_name : '_undefined'
    const moduleName = module ? module.name : '_undefined'
    const moduleIcon = module ? module.icon : '_undefined'
    const moduleHelpUrl = module ? module.help_url : ''

    const isNoteVisible = this.state.editedNotes !== null || !!this.props.wfModule.notes

    const notes = (
      <div className={`module-notes${isNoteVisible ? ' visible' : ''}`}>
        <EditableNotes
          isReadOnly={isReadOnly}
          inputRef={this.notesInputRef}
          placeholder='Type a note...'
          value={this.state.editedNotes === null ? (this.props.wfModule.notes || '') : this.state.editedNotes}
          onChange={this.onChangeNote}
          onFocus={this.onFocusNote}
          onBlur={this.onBlurNote}
          onCancel={this.onCancelNote}
        />
      </div>
    )

    let alertButton = null
    if (this.props.fetchModuleExists && !isReadOnly && !this.props.isAnonymous) {
      const notifications = wfModule.notifications
      const hasUnseen = wfModule.has_unseen_notification
      let className = 'notifications'
      if (notifications) className += ' enabled'
      if (hasUnseen) className += ' has-unseen'
      const title = notifications ? 'Email alerts enabled' : 'Email alerts disabled'

      alertButton = (
        <button title={title} className={className} onClick={this.onClickNotification}>
          <i className={` ${hasUnseen ? 'icon-notification-filled' : 'icon-notification'}`} />
        </button>
      )
    }

    let helpIcon = null
    if (!this.props.isReadOnly) {
      helpIcon = (
        <a title='Help for this module' className='help-button' href={moduleHelpUrl} target='_blank'>
          <i className='icon-help' />
        </a>
      )
    }

    let notesIcon = null
    if (!this.props.isReadOnly) {
      notesIcon = (
        <button
          title='Edit Note'
          className={'btn edit-note' + (this.props.isLessonHighlightNotes ? ' lesson-highlight' : '')}
          onClick={this.focusNote}
        >
          <i className='icon-note' />
        </button>
      )
    }

    let contextMenu = null
    if (!this.props.isReadOnly) {
      contextMenu = (
        <WfModuleContextMenu
          removeModule={this.removeModule}
          id={wfModule.id}
        />
      )
    }

    // Set opacity to 0/1 instead of just not rendering these elements, so that any children that these
    // buttons create (e.g. export dialog) are still visible. Can't use display: none as we need display: flex
    // Fixes https://www.pivotaltracker.com/story/show/154033690
    const contextBtns = (
      <div className='context-buttons'>
        {this.renderZenModeButton()}
        {alertButton}
        {helpIcon}
        {notesIcon}
        {contextMenu}
      </div>
    )

    const moduleIconClassName = 'icon-' + moduleIcon + ' WFmodule-icon'

    let maybeDataVersionModal = null
    if (this.state.isDataVersionModalOpen) {
      maybeDataVersionModal = (
        <DataVersionModal
          wfModuleId={wfModule.id}
          onClose={this.onCloseDataVersionModal}
        />
      )
    }

    let className = 'wf-module status-' + this.wfModuleStatus
    className += this.state.isDragging ? ' dragging' : ''
    className += this.props.isSelected ? ' selected' : ''
    className += this.props.isAfterSelected ? ' after-selected' : ''
    className += this.isEditing ? ' editing' : ''
    if (this.props.isLessonHighlight) className += ' lesson-highlight'
    if (this.props.isZenMode) className += ' zen-mode'

    // Putting it all together: name, status, parameters, output
    return (
      <div
        className={className}
        data-module-slug={moduleSlug}
        data-module-name={moduleName}
        onMouseDown={this.onMouseDown}
      >
        {notes}
        <h3>{numberFormat.format(index + 1)}</h3>
        <div className="module-card-and-link">
          <div className='module-card' draggable={!isReadOnly && !!this.props.onDragStart} onDragStart={this.onDragStart} onDragEnd={this.onDragEnd}>
            <div className='module-card-header'>
              <div className='controls'>
                <WfModuleCollapseButton
                  isCollapsed={wfModule.is_collapsed}
                  isLessonHighlight={this.props.isLessonHighlightCollapse}
                  onCollapse={this.collapse}
                  onExpand={this.expand}
                />
                <i className={moduleIconClassName} />
                <div className='module-name'>{moduleName}</div>
                {contextBtns}
              </div>
              {(!isReadOnly) ? (
                <DeprecationNotice
                  helpUrl={moduleHelpUrl}
                  message={module && module.deprecated ? module.deprecated.message : null}
                />
              ) : null}
            </div>
            <div className={`module-card-details ${wfModule.is_collapsed ? 'collapsed' : 'expanded'}`}>
              {/* --- Error message --- */}
              <StatusLine
                module={module}
                status={this.wfModuleStatus}
                error={wfModule.output_error || ''}
                quickFixes={wfModule.quick_fixes || []}
                applyQuickFix={this.applyQuickFix}
              />
              {this.props.module && !wfModule.is_collapsed ? (
                /*
                 * We only render <ParamsForm> when not collapsed. That's so
                 * that params are visible when mounted -- so they can
                 * auto-size themselves.
                 *
                 * It also saves us from unnecessary HTTP requests for
                 * collapsed modules like Refine that make HTTP requests to
                 * display their components.
                 */
                <ErrorBoundary>
                  <ParamsForm
                    isReadOnly={this.props.isReadOnly}
                    isZenMode={this.props.isZenMode}
                    api={this.props.api}
                    fields={this.props.module.param_fields}
                    value={this.props.wfModule ? this.props.wfModule.params : null}
                    edits={this.state.edits}
                    wfModuleId={this.props.wfModule ? this.props.wfModule.id : null}
                    wfModuleOutputError={this.props.wfModule ? this.props.wfModule.output_error : null}
                    isWfModuleBusy={this.wfModuleStatus === 'busy'}
                    inputWfModuleId={inputWfModule ? inputWfModule.id : null}
                    inputDeltaId={inputWfModule ? (inputWfModule.cached_render_result_delta_id || null) : null}
                    inputColumns={inputWfModule ? inputWfModule.output_columns : null}
                    tabs={tabs}
                    currentTab={currentTab}
                    applyQuickFix={this.applyQuickFix}
                    startCreateSecret={this.startCreateSecret}
                    deleteSecret={this.deleteSecret}
                    getParamText={this.getParamText}
                    onChange={this.onChange}
                    onSubmit={this.onSubmit}
                  />
                </ErrorBoundary>
              ) : null}
            </div>
          </div>
        </div>
        {maybeDataVersionModal}
      </div>
    )
  }
}

class WfModuleCollapseButton extends React.PureComponent {
  static propTypes = {
    isCollapsed: PropTypes.bool.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    onCollapse: PropTypes.func.isRequired, // func() => undefined
    onExpand: PropTypes.func.isRequired // func() => undefined
  }

  render () {
    const { isCollapsed, isLessonHighlight, onCollapse, onExpand } = this.props

    const iconClass = isCollapsed ? 'icon-caret-right' : 'icon-caret-down'
    const onClick = isCollapsed ? onExpand : onCollapse
    const name = isCollapsed ? 'expand module' : 'collapse module'
    const lessonHighlightClass = isLessonHighlight ? 'lesson-highlight' : ''
    return (
      <button name={name} className='workflow-step-collapse' onClick={onClick}>
        <i className={`context-collapse-button ${iconClass} ${lessonHighlightClass}`} />
      </button>
    )
  }
}

const getWorkflow = ({ workflow }) => workflow
const getReadyTabs = ({ tabs }) => tabs
const getPendingTabs = ({ pendingTabs }) => pendingTabs || {}
const getReadyAndPendingTabs = createSelector([ getReadyTabs, getPendingTabs ], (readyTabs, pendingTabs) => {
  return {
    ...pendingTabs,
    ...readyTabs
  }
})
const getWfModules = ({ wfModules }) => wfModules
const getTabs = createSelector([ getWorkflow, getReadyAndPendingTabs, getWfModules ], (workflow, tabs, wfModules) => {
  return workflow.tab_slugs.map(slug => {
    const tab = tabs[slug]
    let outputColumns = null
    if (tab.wf_module_ids.length > 0) {
      const lastIndex = tab.wf_module_ids.length - 1
      if (lastIndex >= 0) {
        const lastWfModuleId = tab.wf_module_ids[lastIndex]
        const lastWfModule = wfModules[lastWfModuleId] // null if placeholder
        if (lastWfModule && lastWfModule.last_relevant_delta_id === lastWfModule.cached_render_result_delta_id) {
          outputColumns = lastWfModule.output_columns
        }
      }
    }
    return {
      slug,
      name: tab.name,
      outputColumns
    }
  })
})
const getCurrentTab = createSelector([ getWorkflow, getReadyAndPendingTabs ], (workflow, tabs) => {
  const tabSlug = workflow.tab_slugs[workflow.selected_tab_position]
  return tabs[tabSlug]
})
const getModules = ({ modules }) => modules

/**
 * Find first WfModule index that has a `.loads_data` ModuleVersion, or `null`
 */
const firstFetchIndex = createSelector([ getCurrentTab, getWfModules, getModules ], (tab, wfModules, modules) => {
  const index = tab.wf_module_ids.findIndex(id => {
    const wfModule = wfModules[String(id)]
    if (!wfModule) return false // add-module not yet loaded
    const module = modules[wfModule.module]
    return module ? module.loads_data : false
  })
  return index === -1 ? null : index
})

function mapStateToProps (state, ownProps) {
  const { testHighlight } = lessonSelector(state)
  const { index } = ownProps
  const moduleIdName = ownProps.wfModule.module || null
  const module = moduleIdName ? state.modules[moduleIdName] : null
  const moduleName = module ? module.name : null
  const fetchIndex = firstFetchIndex(state)

  return {
    module,
    tabs: getTabs(state),
    currentTab: getCurrentTab(state).slug,
    isZenModeAllowed: module ? !!module.has_zen_mode : false,
    isLessonHighlight: testHighlight({ type: 'WfModule', index, moduleName }),
    isLessonHighlightCollapse: testHighlight({ type: 'WfModuleContextButton', button: 'collapse', index, moduleName }),
    isLessonHighlightNotes: testHighlight({ type: 'WfModuleContextButton', button: 'notes', index, moduleName }),
    isReadOnly: state.workflow.read_only,
    isAnonymous: state.workflow.is_anonymous,
    fetchModuleExists: fetchIndex !== null && fetchIndex <= index
  }
}

const mapDispatchToProps = {
  clearNotifications: clearNotificationsAction,
  setSelectedWfModule: setSelectedWfModuleAction,
  setWfModuleCollapsed: setWfModuleCollapsedAction,
  setWfModuleParams: setWfModuleParamsAction,
  maybeRequestFetch: maybeRequestWfModuleFetchAction,
  applyQuickFix: quickFixAction,
  setWfModuleNotes: setWfModuleNotesAction,
  deleteSecret: deleteSecretAction,
  startCreateSecret: startCreateSecretAction,
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(WfModule)
