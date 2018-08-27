// UI for a single module within a workflow

import React from 'react'
import DataVersionModal from '../DataVersionModal'
import WfParameter from '../WfParameter'
import WfModuleContextMenu from '../WfModuleContextMenu'
import EditableNotes from '../EditableNotes'
import StatusBar from './StatusBar'
import StatusLine from './StatusLine'
import {
  setWfModuleCollapsedAction,
  clearNotificationsAction,
  setSelectedWfModuleAction,
  setParamValueAction
} from '../workflow-reducer'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import lessonSelector from '../lessons/lessonSelector'
import { createSelector } from 'reselect'

// ---- WfModule ----
export class WfModule extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    isZenMode: PropTypes.bool.isRequired,
    index: PropTypes.number.isRequired,
    wfModule: PropTypes.object,
    inputWfModule: PropTypes.shape({
      id: PropTypes.number.isRequired,
      last_relevant_delta_id: PropTypes.number,
      output_columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      })), // or null
    }), // or null
    module: PropTypes.object,
    selected: PropTypes.bool,
    changeParam: PropTypes.func, // func(paramId, { value: newVal }) => undefined -- icky, prefer onChange
    removeModule: PropTypes.func,
    api: PropTypes.object.isRequired,
    onDragStart: PropTypes.func.isRequired, // func({ type:'WfModule',id,index }) => undefined
    onDragEnd: PropTypes.func.isRequired, // func() => undefined
    focusModule: PropTypes.func, // func(HTMLElement) => undefined (should be called scrollToHtmlElement(el))
    isLessonHighlight: PropTypes.bool.isRequired,
    isLessonHighlightNotes: PropTypes.bool.isRequired,
    isLessonHighlightCollapse: PropTypes.bool.isRequired,
    fetchModuleExists: PropTypes.bool.isRequired, // there is a fetch module anywhere in the workflow
    clearNotifications: PropTypes.func.isRequired, // func() => undefined
    setSelectedWfModule: PropTypes.func.isRequired, // func(index) => undefined
    setWfModuleCollapsed: PropTypes.func.isRequired, // func(wfModuleId, isCollapsed, isReadOnly) => undefined
    setZenMode: PropTypes.func.isRequired // func(wfModuleId, bool) => undefined
  }

  constructor (props) {
    super(props)

    this.changeParam = this.changeParam.bind(this)
    this.setParamText = this.setParamText.bind(this)
    this.getParamText = this.getParamText.bind(this)
    this.getParamMenuItems = this.getParamMenuItems.bind(this)
    this.removeModule = this.removeModule.bind(this)
    this.setModuleRef = this.setModuleRef.bind(this)
    this.moduleRef = null
    this.notesInputRef = React.createRef()

    this.state = {
      notes: this.props.wfModule.notes || '',
      isNoteForcedVisible: false,
      isDataVersionModalOpen: false,
      isDragging: false,
      edits: {} // id_name => newValue
    }
  }

  onClickNotification = () => {
    this.props.clearNotifications(this.props.wfModule.id)

    this.setState({
      isDataVersionModalOpen: true
    })
  }

  // Scroll when we create a new wfmodule
  componentDidMount () {
    if (this.props.selected) {
      this.props.focusModule(this.moduleRef)
    }
  }

  // We become the selected module on any click
  click = (e) => {
    this.props.setSelectedWfModule(this.props.index)
  }

  changeParam (id, payload) {
    this.props.changeParam(id, payload)
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

  // These functions allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  // Suppresses reassignment of the same text, which can be important to avoid endless notification loops
  setParamText (paramIdName, text) {
    const p = this.getParameterValue(paramIdName)
    if (p && text !== p.string) {
      this.props.changeParam(p.id, { value: text })
    }
  }

  getParamText (paramIdName) {
    const p = this.getParameterValue(paramIdName)
    return p ? p.value : null
  }

  getParamId = (paramIdName) => {
    const p = this.getParameterValue(paramIdName)
    return p ? p.id : null
  }

  getParamMenuItems (paramIdName) {
    const p = this.getParameterValue(paramIdName)

    if (p) {
      if (p.menu_items) {
        return p.menu_items.split('|').map(s => s.trim())
      }
    }
    return []
  }

  removeModule (e) {
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

  setModuleRef (ref) {
    this.moduleRef = ref
  }

  onChangeIsZenMode = (ev) => {
    this.props.setZenMode(this.props.wfModule.id, ev.target.checked)
  }

  renderZenModeButton () {
    const { wfModule, module, isZenMode } = this.props
    const zenModeAllowed = module.has_zen_mode

    if (!zenModeAllowed) return null

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
      edits: Object.assign({}, this.state.edits, { [idName]: newValue })
    })
  }

  /*
   * Tell the server to reload data from upstream.
   *
   * Only works if there is a 'version_select' custom parameter.
   *
   * TODO put this in reducer. (That implies it must affect state. It doesn't now.)
   */
  maybeRequestFetch = () => {
    const value = this.getParameterValue('version_select')
    if (value) {
      this.props.api.postParamEvent(value.id)
    }
  }

  onSubmit = () => {
    const { edits } = this.state

    this.setState({ edits: {} })

    for (const name of Object.keys(edits)) {
      const value = edits[name]
      const id = this.getParamId(name)
      this.props.changeParam(id, value)
    }

    this.maybeRequestFetch()
  }

  onReset = (idName) => {
    const oldEdits = this.state.edits
    if (!(idName in oldEdits)) return

    const edits = Object.assign({}, oldEdits)
    delete edits[idName]
    this.setState({ edits })
  }

  renderParam = (p, index) => {
    const { api, wfModule, module, isReadOnly, isZenMode, inputWfModule } = this.props
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
        moduleName={module.name}
        isReadOnly={isReadOnly}
        isZenMode={isZenMode}
        wfModuleStatus={wfModule.status}
        wfModuleError={wfModule.error_msg}
        key={index}
        p={p}
        onChange={this.onChange}
        onSubmit={this.onSubmit}
        onReset={this.onReset}
        value={value}
        changeParam={this.changeParam}
        wfModuleId={wfModule.id}
        inputWfModuleId={inputWfModule ? inputWfModule.id : null}
        inputLastRelevantDeltaId={inputWfModule ? inputWfModule.last_relevant_delta_id : null}
        inputColumns={inputWfModule ? inputWfModule.output_columns : null}
        updateSettings={updateSettings}
        getParamId={this.getParamId}
        getParamText={this.getParamText}
        getParamMenuItems={this.getParamMenuItems}
        setParamText={this.setParamText}
      />
    )
  }

  render () {
    const { isReadOnly, wfModule, module } = this.props

    // Each parameter gets a WfParameter
    const paramdivs = wfModule.parameter_vals.map(this.renderParam)

    const notes = (
      <div className={`module-notes${(!!this.state.notes || this.state.isNoteForcedVisible) ? ' visible' : ''}`}>
        <EditableNotes
          isReadOnly={isReadOnly}
          inputRef={this.notesInputRef}
          placeholder='Type something'
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
        <a title='Help for this module' className='help-button' href={module.help_url} target='_blank'>
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

    const moduleIcon = 'icon-' + module.icon + ' WFmodule-icon'

    let maybeDataVersionModal = null
    if (this.state.isDataVersionModalOpen) {
      maybeDataVersionModal = (
        <DataVersionModal
          wfModuleId={wfModule.id}
          onClose={this.onCloseDataVersionModal}
        />
      )
    }

    let className = 'wf-module'
    className += wfModule.status ? ` status-${wfModule.status}` : ''
    className += wfModule.is_collapsed ? ' collapsed' : ' expanded'
    if (this.props.isLessonHighlight) className += ' lesson-highlight'
    if (this.props.isZenMode) className += ' zen-mode'

    // Putting it all together: name, status, parameters, output
    return (
      <div onClick={this.click} className={className} data-module-name={module.name}>
        {notes}
        <div className={'wf-card ' + (this.state.isDragging ? 'dragging ' : '')} ref={this.setModuleRef} draggable={!this.props.isReadOnly} onDragStart={this.onDragStart} onDragEnd={this.onDragEnd}>

          <div>
            <div className='output-bar-container'>
              <StatusBar status={wfModule.status} isSelected={this.props.selected} isDragging={this.state.isDragging} />
            </div>
            <div className='module-content'>
              <div className='module-card-header'>
                <WfModuleCollapseButton
                  isCollapsed={wfModule.is_collapsed}
                  isLessonHighlight={this.props.isLessonHighlightCollapse}
                  onCollapse={this.collapse}
                  onExpand={this.expand}
                />
                <i className={moduleIcon} />
                <div className='module-name'>{module.name}</div>
                {contextBtns}
              </div>
              {/* --- Error message --- */}
              <StatusLine status={wfModule.status} error_msg={wfModule.error_msg} />
              <div className='module-card-params'>
                {paramdivs}
              </div>
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
const getWfModules = ({ wfModules }) => wfModules
const getModules = ({ modules }) => modules
/**
 * Find first WfModule that has a `.loads_data` ModuleVersion.
 */
const hasFetchWfModule = createSelector([ getWorkflow, getWfModules, getModules ], (workflow, wfModules, modules) => {
  const wfModuleIds = workflow.wf_modules
  if (!wfModuleIds) return false
  for (let wfModuleId of wfModuleIds) {
    const wfModule = wfModules[String(wfModuleId)]
    if (wfModule) {
      const moduleId = wfModule.module_version ? wfModule.module_version.module : null
      if (moduleId) {
        const module = modules[String(moduleId)]
        if (module) {
          if (module.loads_data) return true
        }
      }
    }
  }
  return false
})

function mapStateToProps (state, ownProps) {
  const { testHighlight } = lessonSelector(state)
  const { index } = ownProps
  const module = ownProps.wfModule.module_version ? state.modules[String(ownProps.wfModule.module_version.module)] : null
  const moduleName = module ? module.name : null
  return {
    module,
    isLessonHighlight: testHighlight({ type: 'WfModule', index, moduleName }),
    isLessonHighlightCollapse: testHighlight({ type: 'WfModuleContextButton', button: 'collapse', index, moduleName }),
    isLessonHighlightNotes: testHighlight({ type: 'WfModuleContextButton', button: 'notes', index, moduleName }),
    isReadOnly: state.workflow.read_only,
    isAnonymous: state.workflow.is_anonymous,
    fetchModuleExists: hasFetchWfModule(state)
  }
}

function mapDispatchToProps (dispatch) {
  return {
    clearNotifications (wfModuleId) {
      dispatch(clearNotificationsAction(wfModuleId))
    },

    setSelectedWfModule (index) {
      dispatch(setSelectedWfModuleAction(index))
    },

    setWfModuleCollapsed (wfModuleId, isCollapsed, isReadOnly) {
      dispatch(setWfModuleCollapsedAction(wfModuleId, isCollapsed, isReadOnly))
    },

    changeParam (paramId, newVal) {
      const action = setParamValueAction(paramId, newVal)
      dispatch(action)
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(WfModule)
