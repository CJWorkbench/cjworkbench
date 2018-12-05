// UI for a single module within a workflow

import React from 'react'
import DataVersionModal from '../DataVersionModal'
import WfParameter from '../WfParameter'
import WfModuleContextMenu from './WfModuleContextMenu'
import EditableNotes from '../EditableNotes'
import StatusLine from './StatusLine'
import {
  clearNotificationsAction,
  maybeRequestWfModuleFetchAction,
  quickFixAction,
  setSelectedWfModuleAction,
  setWfModuleParamsAction,
  setWfModuleCollapsedAction
} from '../workflow-reducer'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import lessonSelector from '../lessons/lessonSelector'
import { createSelector } from 'reselect'
import { findParamValByIdName } from '../utils'

const numberFormat = new Intl.NumberFormat()

// ---- WfModule ----
export class WfModule extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    isZenMode: PropTypes.bool.isRequired,
    isZenModeAllowed: PropTypes.bool.isRequired,
    moduleHelpUrl: PropTypes.string, // or null
    moduleName: PropTypes.string, // or null
    moduleIcon: PropTypes.string, // or null
    tabId: PropTypes.number.isRequired,
    index: PropTypes.number.isRequired,
    wfModule: PropTypes.object,
    inputWfModule: PropTypes.shape({
      id: PropTypes.number.isRequired,
      last_relevant_delta_id: PropTypes.number,
      cached_render_result_delta_id: PropTypes.number, // or null
      output_columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      })) // or null
    }), // or null
    module: PropTypes.object,
    isSelected: PropTypes.bool.isRequired,
    isAfterSelected: PropTypes.bool.isRequired,
    setWfModuleParams: PropTypes.func, // func(wfModuleId, { paramidname: newVal }) => undefined -- icky, prefer onChange
    removeModule: PropTypes.func,
    api: PropTypes.object.isRequired,
    onDragStart: PropTypes.func.isRequired, // func({ type:'WfModule',id,index }) => undefined
    onDragEnd: PropTypes.func.isRequired, // func() => undefined
    isLessonHighlight: PropTypes.bool.isRequired,
    isLessonHighlightNotes: PropTypes.bool.isRequired,
    isLessonHighlightCollapse: PropTypes.bool.isRequired,
    fetchModuleExists: PropTypes.bool.isRequired, // there is a fetch module anywhere in the workflow
    clearNotifications: PropTypes.func.isRequired, // func() => undefined
    maybeRequestFetch: PropTypes.func.isRequired, // func(wfModuleId) => undefined
    setSelectedWfModule: PropTypes.func.isRequired, // func(tabId, index) => undefined
    setWfModuleCollapsed: PropTypes.func.isRequired, // func(wfModuleId, isCollapsed, isReadOnly) => undefined
    setZenMode: PropTypes.func.isRequired, // func(wfModuleId, bool) => undefined
    applyQuickFix: PropTypes.func.isRequired, // func(wfModuleId, action, args) => undefined
  }

  constructor (props) {
    super(props)

    this.getParamText = this.getParamText.bind(this)
    this.notesInputRef = React.createRef()

    this.state = {
      notes: this.props.wfModule.notes || '',
      isNoteForcedVisible: false,
      isDataVersionModalOpen: false,
      isDragging: false,
      edits: {} // id_name => newValue
    }
  }

  /**
   * Overwrite some params on this WfModule.
   *
   * TODO nix this entirely? onChange and onSubmit are more appropriate.
   * [2018-11-22, adamhooper] I can't see any place this function belongs,
   * because we don't have any params that should write to _other_ params.
   * (Especially not our multi-column selector.)
   */
  setWfModuleParams = (params) => {
    this.props.setWfModuleParams(this.props.wfModule.id, params)
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
      this.props.setSelectedWfModule(this.props.index)
    }
  }

  onDragStart = (ev) => {
    if (ev.target.tagName in {
      'button': null,
      'input': null,
      'select': null,
      'textarea': null,
      'label': null
    }) {
      // Don't drag when user selects text
      ev.preventDefault()
      return
    }

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
    return this.props.wfModule.parameter_vals.find(p => p.parameter_spec.id_name === idName)
  }

  // Allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  getParamText (paramIdName) {
    const p = this.getParameterValue(paramIdName)
    return p ? p.value : null
  }

  getParamId = (paramIdName) => {
    const p = this.getParameterValue(paramIdName)
    return p ? p.id : null
  }

  getParamMenuItems = (paramIdName) => {
    const p = this.getParameterValue(paramIdName)

    if (p) {
      if (p.items) {
        return p.items.split('|').map(s => s.trim())
      }
    }
    return []
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
    if (ref) {
      this.setState({ isNoteForcedVisible: true })
      ref.focus()
      ref.select()
    }
  }

  onChangeNote = (ev) => {
    this.setState({ notes: ev.target.value })
  }

  onFocusNote = () => {
    this.setState({ isNoteForcedVisible: true })
  }

  onBlurNote = (ev) => {
    if (this.state.notes !== (this.props.wfModule.notes || '')) {
      // TODO use a reducer action
      this.props.api.setWfModuleNotes(this.props.wfModule.id, this.state.notes)
    }
    this.setState({ isNoteForcedVisible: false })
  }

  onCancelNote = (ev) => {
    this.setState({ notes: this.props.wfModule.notes })
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

  onChange = (idName, newValue) => {
    this.setState({
      edits: { ...this.state.edits, [idName]: newValue }
    })
  }

  onSubmit = () => {
    const { edits } = this.state

    this.props.setWfModuleParams(this.props.wfModule.id, edits)
    this.setState({ edits: {} })

    this.props.maybeRequestFetch(this.props.wfModule.id)
  }

  onReset = (idName) => {
    const oldEdits = this.state.edits
    if (!(idName in oldEdits)) return

    const edits = Object.assign({}, oldEdits)
    delete edits[idName]
    this.setState({ edits })
  }

  get wfModuleStatus () {
    // TODO don't copy/paste from OutputPane.js
    const { wfModule } = this.props
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

  // checks visible_if fields, recursively (we are not visible if parent referenced in visbile_if is not visible)
  isParameterVisible(p, breadcrumbs=[]) {
    const id_name = p.parameter_spec.id_name
    if (breadcrumbs.includes(id_name)) {
      throw new Error(`visible_if infinite loop: ${[ ...breadcrumbs, id_name ].join(' -> ')}`)
    }

    // No visibility condition, we are visible
    const visibleIf = p.parameter_spec.visible_if
    if (!visibleIf) {
      return true
    }

    const condition = JSON.parse(visibleIf)
    const invert = condition['invert'] === true

    // missing id_name, default to visible
    if (!('id_name' in condition)) {
      return true
    }

    // We are invisible if our parent is invisible
    const parent = findParamValByIdName(this.props.wfModule, condition['id_name'])
    if (!parent || !this.isParameterVisible(parent, [ ...breadcrumbs, id_name ])) {
      return false
    }

    if ('value' in condition) {
      const value = this.getParamText(condition['id_name'])

      // If the condition value is a boolean:
      if (typeof condition['value'] === typeof true || typeof condition['value'] === typeof 0) {
        let match
        if (value === condition['value']) {
          // Just return if it matches
          match = true
        } else if (typeof condition['value'] === typeof true && typeof value !== typeof true) {
          // If value: true or value: false, return whether string is set
          match = condition['value'] === (value !== '')
        } else {
          match = false
        }
        return invert !== match
      }

      // Otherwise, if it's a menu item:
      const condValues = condition['value'].split('|').map(cond => cond.trim())
      const selectionIdx = parseInt(value)
      if (!isNaN(selectionIdx)) {
        const menuItems = this.getParamMenuItems(condition['id_name'])
        if (menuItems.length > selectionIdx) {
          const selection = menuItems[selectionIdx]
          const selectionInCondition = (condValues.indexOf(selection) >= 0)
          return invert !== selectionInCondition
        }
      }
    }

    // If the visibility condition is empty or invalid, default to showing the parameter
    return true
  }

  renderParam = (p, index) => {
    if (!this.isParameterVisible(p)) {
      return null
    }

    const { api, wfModule, moduleName, isReadOnly, isZenMode, inputWfModule } = this.props
    const updateSettings = {
      lastUpdateCheck: wfModule.last_update_check,
      autoUpdateData: wfModule.auto_update_data,
      updateInterval: wfModule.update_interval,
      updateUnits: wfModule.update_units
    }

    const { edits } = this.state
    const idName = p.parameter_spec.id_name

    const value = idName in edits ? edits[idName] : p.value

    // We'll pass name=idName for unit tests, for now. In the future, we should
    // nix `p` entirely and mass-rename `idName` to `slug`/`name` as
    // appropriate (here, `name` is appropriate because it's like the HTML
    // `name` attribute). TODO add `name` to WfParameter.propTypes.
    return (
      <WfParameter
        api={api}
        name={idName}
        moduleName={moduleName}
        isReadOnly={isReadOnly}
        isZenMode={isZenMode}
        wfModuleStatus={this.wfModuleStatus}
        wfModuleOutputError={wfModule.output_error}
        key={index}
        p={p}
        onChange={this.onChange}
        onSubmit={this.onSubmit}
        onReset={this.onReset}
        value={value}
        setWfModuleParams={this.setWfModuleParams}
        wfModuleId={wfModule.id}
        inputWfModuleId={inputWfModule ? inputWfModule.id : null}
        inputDeltaId={inputWfModule ? inputWfModule.cached_render_result_delta_id : null}
        inputColumns={inputWfModule ? inputWfModule.output_columns : null}
        updateSettings={updateSettings}
        getParamId={this.getParamId}
        getParamText={this.getParamText}
        getParamMenuItems={this.getParamMenuItems}
      />
    )
  }

  render () {
    const { isReadOnly, index, wfModule, module, moduleHelpUrl, moduleName, moduleIcon } = this.props

    // Each parameter gets a WfParameter
    const paramdivs = moduleName ? wfModule.parameter_vals.map(this.renderParam) : null

    const notes = (
      <div className={`module-notes${(!!this.state.notes || this.state.isNoteForcedVisible) ? ' visible' : ''}`}>
        <EditableNotes
          isReadOnly={isReadOnly}
          inputRef={this.notesInputRef}
          placeholder='Type a note...'
          value={this.state.notes}
          onChange={this.onChangeNote}
          onFocus={this.onFocusNote}
          onBlur={this.onBlurNote}
          onCancel={this.onCancelNote}
        />
      </div>
    )

    let alertButton
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

    let helpIcon
    if (!this.props.isReadOnly) {
      helpIcon = (
        <a title='Help for this module' className='help-button' href={moduleHelpUrl} target='_blank'>
          <i className='icon-help' />
        </a>
      )
    }

    let notesIcon
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

    let contextMenu
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
    if (this.props.isLessonHighlight) className += ' lesson-highlight'
    if (this.props.isZenMode) className += ' zen-mode'

    // Putting it all together: name, status, parameters, output
    return (
      <div
        className={className}
        data-module-name={moduleName}
        onMouseDown={this.onMouseDown}
      >
        {notes}
        <h3>{numberFormat.format(index + 1)}</h3>
        <div className='module-card' draggable={!this.props.isReadOnly} onDragStart={this.onDragStart} onDragEnd={this.onDragEnd}>
          <div className='module-card-header'>
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
          <div className={`module-card-details ${wfModule.is_collapsed ? 'collapsed' : 'expanded'}`}>
            {/* --- Error message --- */}
            <StatusLine
              status={this.wfModuleStatus}
              error={wfModule.output_error || ''}
              quickFixes={wfModule.quick_fixes || []}
              applyQuickFix={this.applyQuickFix}
            />
            <div className='module-card-params'>
              {paramdivs}
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
      <button name={name} className='wf-module-collapse' onClick={onClick}>
        <i className={`context-collapse-button ${iconClass} ${lessonHighlightClass}`} />
      </button>
    )
  }
}

const getWorkflow = ({ workflow }) => workflow
const getTabs = ({ tabs }) => tabs
const getWfModules = ({ wfModules }) => wfModules
const getSelectedTab = createSelector([ getWorkflow, getTabs ], (workflow, tabs) => {
  return tabs[String(workflow.tab_ids[workflow.selected_tab_position])]
})
const getModules = ({ modules }) => modules

/**
 * Find first WfModule index that has a `.loads_data` ModuleVersion, or `null`
 */
const firstFetchIndex = createSelector([ getSelectedTab, getWfModules, getModules ], (tab, wfModules, modules) => {
  const index = tab.wf_module_ids.findIndex(id => {
    const wfModule = wfModules[String(id)]
    if (!wfModule) return false // add-module not yet loaded
    const moduleId = wfModule.module_version ? wfModule.module_version.module : null
    const module = modules[String(moduleId)]
    return module ? module.loads_data : false
  })
  return index === -1 ? null : index
})

function mapStateToProps (state, ownProps) {
  const { testHighlight } = lessonSelector(state)
  const { index } = ownProps
  const module = ownProps.wfModule.module_version ? state.modules[String(ownProps.wfModule.module_version.module)] : null
  const moduleName = module ? module.name : null
  const fetchIndex = firstFetchIndex(state)

  return {
    module,
    moduleName,
    moduleIcon: module ? module.icon : null,
    moduleHelpUrl: module ? module.help_url : null,
    isZenModeAllowed: module ? !!module.has_zen_mode : false,
    isLessonHighlight: testHighlight({ type: 'WfModule', index, moduleName }),
    isLessonHighlightCollapse: testHighlight({ type: 'WfModuleContextButton', button: 'collapse', index, moduleName }),
    isLessonHighlightNotes: testHighlight({ type: 'WfModuleContextButton', button: 'notes', index, moduleName }),
    isReadOnly: state.workflow.read_only,
    isAnonymous: state.workflow.is_anonymous,
    fetchModuleExists: fetchIndex !== null && fetchIndex <= index
  }
}

function mapDispatchToProps (dispatch) {
  return {
    clearNotifications (wfModuleId) {
      dispatch(clearNotificationsAction(wfModuleId))
    },

    setSelectedWfModule (tabId, index) {
      dispatch(setSelectedWfModuleAction(tabId, index))
    },

    setWfModuleCollapsed (wfModuleId, isCollapsed, isReadOnly) {
      dispatch(setWfModuleCollapsedAction(wfModuleId, isCollapsed, isReadOnly))
    },

    setWfModuleParams (wfModuleId, params) {
      dispatch(setWfModuleParamsAction(wfModuleId, params))
    },

    maybeRequestFetch (wfModuleId) {
      dispatch(maybeRequestWfModuleFetchAction(wfModuleId))
    },

    applyQuickFix (wfModuleId, action, args) {
      dispatch(quickFixAction(action, wfModuleId, args))
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(WfModule)
