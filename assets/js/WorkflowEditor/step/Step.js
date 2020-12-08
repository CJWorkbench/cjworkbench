import React from 'react'
import DataVersionModal from '../DataVersionModal'
import ErrorBoundary from '../../ErrorBoundary'
import ParamsForm from '../../params/ParamsForm'
import EditableNotes from '../../EditableNotes'
import DeprecationNotice from './DeprecationNotice'
import StatusLine from './StatusLine'
import {
  clearNotificationsAction,
  startCreateSecretAction,
  deleteSecretAction,
  maybeRequestStepFetchAction,
  quickFixAction,
  setSelectedStepAction,
  setStepParamsAction,
  setStepSecretAction,
  setStepCollapsedAction,
  setStepNotesAction
} from '../../workflow-reducer'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import deepEqual from 'fast-deep-equal'
import lessonSelector from '../../lessons/lessonSelector'
import { createSelector } from 'reselect'
import { i18n } from '@lingui/core'
import { t } from '@lingui/macro'

/**
 * A single step within a tab
 */
export class Step extends React.PureComponent {
  static propTypes = {
    isOwner: PropTypes.bool.isRequired, // if true, !isReadOnly and user may edit secrets
    isReadOnly: PropTypes.bool.isRequired,
    isAnonymous: PropTypes.bool.isRequired,
    isZenMode: PropTypes.bool.isRequired,
    isZenModeAllowed: PropTypes.bool.isRequired,
    isDragging: PropTypes.bool.isRequired,
    module: PropTypes.shape({
      id_name: PropTypes.string.isRequired,
      help_url: PropTypes.string.isRequired,
      deprecated: PropTypes.shape({
        message: PropTypes.string.isRequired
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
    workflowId: PropTypes.number.isRequired,
    step: PropTypes.shape({
      id: PropTypes.number.isRequired,
      params: PropTypes.object.isRequired,
      secrets: PropTypes.object.isRequired,
      last_relevant_delta_id: PropTypes.number,
      cached_render_result_delta_id: PropTypes.number, // or null
      output_status: PropTypes.oneOf(['ok', 'unreachable', 'error']) // or null
    }), // null if loading
    inputStep: PropTypes.shape({
      id: PropTypes.number.isRequired,
      last_relevant_delta_id: PropTypes.number,
      cached_render_result_delta_id: PropTypes.number, // or null
      output_columns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'timestamp']).isRequired
      })) // or null
    }), // or null
    isSelected: PropTypes.bool.isRequired,
    isAfterSelected: PropTypes.bool.isRequired,
    setStepParams: PropTypes.func, // func(stepId, { paramidname: newVal }) => undefined
    setStepSecret: PropTypes.func, // func(stepId, param, secret) => undefined
    deleteStep: PropTypes.func,
    api: PropTypes.object.isRequired,
    onDragStart: PropTypes.func, // func({ type:'Step',id,index }) => undefined; null if not draggable
    onDragEnd: PropTypes.func, // func() => undefined
    isLessonHighlight: PropTypes.bool.isRequired,
    isLessonHighlightNotes: PropTypes.bool.isRequired,
    isLessonHighlightCollapse: PropTypes.bool.isRequired,
    fetchModuleExists: PropTypes.bool.isRequired, // there is a fetch module anywhere in the workflow
    clearNotifications: PropTypes.func.isRequired, // func() => undefined
    maybeRequestFetch: PropTypes.func.isRequired, // func(stepId) => undefined
    setSelectedStep: PropTypes.func.isRequired, // func(stepId) => undefined
    setStepCollapsed: PropTypes.func.isRequired, // func(stepId, isCollapsed, isReadOnly) => undefined
    setZenMode: PropTypes.func.isRequired, // func(stepId, bool) => undefined
    applyQuickFix: PropTypes.func.isRequired, // func(stepId, action) => undefined
    setStepNotes: PropTypes.func.isRequired // func(stepId, notes) => undefined
  }

  notesInputRef = React.createRef()

  state = {
    editedNotes: null, // when non-null, input is focused
    isDataVersionModalOpen: false,
    edits: {} // idName => newValue
  }

  get hasFetch () {
    return this.props.fields.some(f => f.type === 'custom' && (f.idName === 'version_select' || f.idName === 'version_select_simpler'))
  }

  get isEditing () {
    return Object.keys(this.state.edits).length > 0
  }

  handleClickNotification = () => {
    this.props.clearNotifications(this.props.step.id)

    this.setState({
      isDataVersionModalOpen: true
    })
  }

  // We become the selected module on any click
  handleMouseDown = () => {
    if (!this.props.isSelected) {
      this.props.setSelectedStep(this.props.step.id)
    }
  }

  startCreateSecret = (paramIdName) => {
    const { startCreateSecret, step } = this.props
    return startCreateSecret(step.id, paramIdName)
  }

  deleteSecret = (paramIdName) => {
    const { deleteSecret, step } = this.props
    return deleteSecret(step.id, paramIdName)
  }

  handleDragStart = (ev) => {
    const dragObject = {
      type: 'Step',
      index: this.props.index,
      id: this.props.step.id,
      slug: this.props.step.slug,
      tabSlug: this.props.currentTab
    }
    ev.dataTransfer.setData('application/json', JSON.stringify(dragObject))
    ev.dataTransfer.effectAllowed = 'move'
    ev.dataTransfer.dropEffect = 'move'
    this.props.onDragStart(dragObject)
  }

  handleDragEnd = (ev) => {
    this.props.onDragEnd()
  }

  handleClickDelete = () => {
    this.props.deleteStep(this.props.step.id)
  }

  // Optimistically updates the state, and then sends the new state to the server,
  // where it's persisted across sessions and through time.
  setCollapsed (isCollapsed) {
    this.props.setStepCollapsed(this.props.step.id, isCollapsed, this.props.isReadOnly)
  }

  handleClickCollapse = () => {
    this.setCollapsed(true)
  }

  handleClickExpand = () => {
    this.setCollapsed(false)
  }

  // when Notes icon is clicked, show notes and start in editable state if not read-only
  handleClickNoteButton = () => {
    const ref = this.notesInputRef.current
    if (ref) { // only if not read-only
      ref.focus() // calls this.handleFocusNote()
    }
  }

  handleChangeNote = (ev) => {
    this.setState({ editedNotes: ev.target.value })
  }

  handleFocusNote = () => {
    if (this.state.editedNotes === null) {
      this.setState({ editedNotes: this.props.step.notes || '' })
    }
  }

  handleBlurNote = () => {
    // Blur may come _immediately_ after cancel -- and before cancel's
    // setState() is processed. Use the callback approach to setState() to
    // make sure we're reading the value written by handleCancelNote()
    this.setState((state, props) => {
      if (state.editedNotes === null) {
        // we canceled
      } else {
        props.setStepNotes(props.step.id, state.editedNotes)
      }
      return { editedNotes: null }
    })
  }

  handleCancelNote = () => {
    this.setState({ editedNotes: null })
  }

  handleCloseDataVersionModal = () => {
    this.setState({
      isDataVersionModalOpen: false
    })
  }

  applyQuickFix = (action) => {
    this.props.applyQuickFix(this.props.step.id, action)
  }

  handleChangeIsZenMode = (ev) => {
    this.props.setZenMode(this.props.step.id, ev.target.checked)
  }

  renderZenModeButton () {
    const { isZenMode, isZenModeAllowed } = this.props

    if (!isZenModeAllowed) return null

    const className = `toggle-zen-mode ${isZenMode ? 'is-zen-mode' : 'not-zen-mode'}`
    const title = isZenMode
      ? t({ id: 'js.WorkflowEditor.step.ZenMode.exit', message: 'exit Zen mode' })
      : t({ id: 'js.WorkflowEditor.step.ZenMode.enter', message: 'enter Zen mode' })

    return (
      <label className={className} title={title}>
        <input type='checkbox' name='zen-mode' checked={isZenMode} onChange={this.handleChangeIsZenMode} />
        <i className='icon-full-screen' />
      </label>
    )
  }

  handleChangeParams = (edits) => {
    this.setState({ edits })
  }

  submitSecret = (param, secret) => {
    const { setStepSecret, step } = this.props
    if (!step) return
    setStepSecret(step.id, param, secret)
  }

  handleSubmitParams = () => {
    const { step, setStepParams, maybeRequestFetch } = this.props

    // We sometimes call onSubmit() _immediately_ after onChange(). onChange()
    // sets this.state.edits, and then onSubmit() should submit them. To make
    // that happen, we need to use the callback version of setState().
    // (this.state.edits is the pre-onChange() data.)
    this.setState(({ edits }) => {
      if (Object.keys(edits).length > 0) {
        setStepParams(step.id, edits).then(() => this.clearUpToDateEdits())
      }

      maybeRequestFetch(step.id)

      // Do not clear "edits" here: at this point, setStepParams() has
      // not updated the Redux state yet, so the edits will flicker away
      // for a fraction of a second. A simple test to prove the problem
      // with `return { edits: {} }`:
      //
      // 1. Paste text data with column "A"
      // 2. Add "Refine" module
      // 3. Choose column "A"
      // 4. Click Submit
      //
      // Expected results: refine values stay put. If we were to
      // `return { edits: {} }`, the refine values would disappear because
      // setStepParams() has not adjusted the state yet, so
      // `reduxState.edits.column` is `""`; we must ensure
      // `this.state.edits.column` is `"A"` until `setStepParams()`
      // completes.
      //
      // We call `this.clearUpToDateEdits()` elsewhere to make sure the edits
      // disappear, so the user sees the module as not-editing.
      return null
    })
  }

  /**
   * Remove from this.state.edits any edits that do not modify a value.
   */
  clearUpToDateEdits () {
    this.setState(({ edits }) => {
      const upstream = this.props.step ? this.props.step.params : {}
      const newEdits = {}
      for (const key in edits) {
        const upstreamValue = upstream[key]
        const editedValue = edits[key]
        if (!deepEqual(upstreamValue, editedValue)) {
          newEdits[key] = editedValue
        }
      }
      return { edits: newEdits }
    })
  }

  get stepStatus () {
    // TODO don't copy/paste from OutputPane.js
    const { step } = this.props
    if (!step) {
      return null
    } else if (
      // We've just sent an HTTP request and not received a response.
      // (This happens after the user clicks to change something -- or clicks
      // "fetch" -- and before the server updates the status.)
      step.nClientRequests > 0 ||

      // The module is performing a fetch
      step.is_busy ||

      // Step is rendering
      step.last_relevant_delta_id !== step.cached_render_result_delta_id ||

      // Step is a placeholder? TODO verify this can actually happen
      !step.output_status
    ) {
      return 'busy'
    } else {
      return step.output_status
    }
  }

  render () {
    const { isReadOnly, index, step, module, inputStep, tabs, currentTab } = this.props

    const moduleSlug = module ? module.id_name : '_undefined'
    const moduleName = module ? module.name : '_undefined'
    const moduleIcon = module ? module.icon : '_undefined'
    const moduleHelpUrl = module ? module.help_url : ''

    const isNoteVisible = this.state.editedNotes !== null || !!this.props.step.notes

    const notes = (
      <div className={`step-notes${isNoteVisible ? ' visible' : ''}`}>
        <EditableNotes
          isReadOnly={isReadOnly}
          inputRef={this.notesInputRef}
          placeholder={t({ id: 'js.WorkflowEditor.step.EditableNotes.placeholder', message: 'Type a note…' })}
          value={this.state.editedNotes === null ? (this.props.step.notes || '') : this.state.editedNotes}
          onChange={this.handleChangeNote}
          onFocus={this.handleFocusNote}
          onBlur={this.handleBlurNote}
          onCancel={this.handleCancelNote}
        />
      </div>
    )

    let alertButton = null
    if (this.props.fetchModuleExists && !isReadOnly && !this.props.isAnonymous) {
      const notifications = step.notifications
      const hasUnseen = step.has_unseen_notification
      let className = 'notifications'
      if (notifications) className += ' enabled'
      if (hasUnseen) className += ' has-unseen'
      const title = notifications
        ? t({ id: 'js.WorkflowEditor.step.alert.enabled', message: 'Email alerts enabled' })
        : t({ id: 'js.WorkflowEditor.step.alert.disabled', message: 'Email alerts disabled' })

      alertButton = (
        <button title={title} className={className} onClick={this.handleClickNotification}>
          <i className={` ${hasUnseen ? 'icon-notification-filled' : 'icon-notification'}`} />
        </button>
      )
    }

    let helpIcon = null
    if (!this.props.isReadOnly) {
      helpIcon = (
        <a
          title={t({ id: 'js.WorkflowEditor.step.help.hoverText', message: 'Help for this module' })}
          className='help-button'
          href={moduleHelpUrl}
          target='_blank'
          rel='noopener noreferrer'
        >
          <i className='icon-help' />
        </a>
      )
    }

    let notesIcon = null
    if (!this.props.isReadOnly) {
      notesIcon = (
        <button
          title={t({ id: 'js.WorkflowEditor.step.notes.edit.hoverText', message: 'Edit Note' })}
          className={'btn edit-note' + (this.props.isLessonHighlightNotes ? ' lesson-highlight' : '')}
          onClick={this.handleClickNoteButton}
        >
          <i className='icon-note' />
        </button>
      )
    }

    let deleteIcon = null
    if (!this.props.isReadOnly) {
      deleteIcon = (
        <button
          title={t({ id: 'js.WorkflowEditor.step.delete.hoverText', message: 'Delete' })}
          className='btn delete-button'
          onClick={this.handleClickDelete}
        >
          <i className='icon-bin' />
        </button>
      )
    }

    const moduleIconClassName = 'icon-' + moduleIcon + ' module-icon'

    let maybeDataVersionModal = null
    if (this.state.isDataVersionModalOpen) {
      maybeDataVersionModal = (
        <DataVersionModal
          stepId={step.id}
          onClose={this.handleCloseDataVersionModal}
        />
      )
    }

    let className = 'step status-' + this.stepStatus
    className += this.props.isDragging ? ' dragging' : ''
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
        onMouseDown={this.handleMouseDown}
      >
        {notes}
        <h3>{i18n.number(index + 1)}</h3>
        <div className='module-card-and-link'>
          <div className='module-card' draggable={!isReadOnly && !!this.props.onDragStart} onDragStart={this.handleDragStart} onDragEnd={this.handleDragEnd}>
            <div className='module-card-header'>
              <div className='controls'>
                <StepCollapseButton
                  isCollapsed={step.is_collapsed}
                  isLessonHighlight={this.props.isLessonHighlightCollapse}
                  onCollapse={this.handleClickCollapse}
                  onExpand={this.handleClickExpand}
                />
                <i className={moduleIconClassName} />
                <div className='module-name'>{moduleName}</div>
                <div className='context-buttons'>
                  {this.renderZenModeButton()}
                  {alertButton}
                  {helpIcon}
                  {notesIcon}
                  {deleteIcon}
                </div>
              </div>
              {(!isReadOnly) ? (
                <DeprecationNotice
                  helpUrl={moduleHelpUrl}
                  message={module && module.deprecated ? module.deprecated.message : null}
                />
              ) : null}
            </div>
            <div className={`module-card-details ${step.is_collapsed ? 'collapsed' : 'expanded'}`}>
              {/* --- Error message --- */}
              <StatusLine
                module={module}
                isReadOnly={isReadOnly}
                status={this.stepStatus}
                errors={step.output_errors || []}
                applyQuickFix={this.applyQuickFix}
              />
              {this.props.module && !step.is_collapsed ? (
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
                    isOwner={this.props.isOwner}
                    isReadOnly={this.props.isReadOnly}
                    isZenMode={this.props.isZenMode}
                    api={this.props.api}
                    fields={this.props.module.param_fields}
                    value={this.props.step ? this.props.step.params : null}
                    secrets={this.props.step ? this.props.step.secrets : null}
                    files={this.props.step ? this.props.step.files : []}
                    edits={this.state.edits}
                    workflowId={this.props.workflowId}
                    stepId={this.props.step ? this.props.step.id : null}
                    stepSlug={this.props.step ? this.props.step.slug : null}
                    stepOutputErrors={this.props.step ? this.props.step.output_errors : []}
                    isStepBusy={this.stepStatus === 'busy'}
                    inputStepId={inputStep ? inputStep.id : null}
                    inputDeltaId={inputStep ? (inputStep.cached_render_result_delta_id || null) : null}
                    inputColumns={inputStep ? inputStep.output_columns : null}
                    tabs={tabs}
                    currentTab={currentTab}
                    applyQuickFix={this.applyQuickFix}
                    startCreateSecret={this.startCreateSecret}
                    submitSecret={this.submitSecret}
                    deleteSecret={this.deleteSecret}
                    onChange={this.handleChangeParams}
                    onSubmit={this.handleSubmitParams}
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

class StepCollapseButton extends React.PureComponent {
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
const getReadyAndPendingTabs = createSelector([getReadyTabs, getPendingTabs], (readyTabs, pendingTabs) => {
  return {
    ...pendingTabs,
    ...readyTabs
  }
})
const getSteps = ({ steps }) => steps
const getTabs = createSelector([getWorkflow, getReadyAndPendingTabs, getSteps], (workflow, tabs, steps) => {
  return workflow.tab_slugs.map(slug => {
    const tab = tabs[slug]
    let outputColumns = null
    if (tab.step_ids.length > 0) {
      const lastIndex = tab.step_ids.length - 1
      if (lastIndex >= 0) {
        const lastStepId = tab.step_ids[lastIndex]
        const lastStep = steps[lastStepId] // null if placeholder
        if (lastStep && lastStep.last_relevant_delta_id === lastStep.cached_render_result_delta_id) {
          outputColumns = lastStep.output_columns
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
const getCurrentTab = createSelector([getWorkflow, getReadyAndPendingTabs], (workflow, tabs) => {
  const tabSlug = workflow.tab_slugs[workflow.selected_tab_position]
  return tabs[tabSlug]
})
const getModules = ({ modules }) => modules

/**
 * Find first Step index that has a `.loads_data` ModuleVersion, or `null`
 */
const firstFetchIndex = createSelector([getCurrentTab, getSteps, getModules], (tab, steps, modules) => {
  const index = tab.step_ids.findIndex(id => {
    const step = steps[String(id)]
    if (!step) return false // add-module not yet loaded
    const module = modules[step.module]
    return module ? module.loads_data : false
  })
  return index === -1 ? null : index
})

function mapStateToProps (state, ownProps) {
  const { testHighlight } = lessonSelector(state)
  const { index } = ownProps
  const moduleIdName = ownProps.step.module || null
  const module = moduleIdName ? state.modules[moduleIdName] : null
  const fetchIndex = firstFetchIndex(state)

  return {
    module,
    tabs: getTabs(state),
    currentTab: getCurrentTab(state).slug,
    isZenModeAllowed: module ? !!module.has_zen_mode : false,
    isLessonHighlight: testHighlight({ type: 'Step', index, moduleIdName }),
    isLessonHighlightCollapse: testHighlight({ type: 'StepContextButton', button: 'collapse', index, moduleIdName }),
    isLessonHighlightNotes: testHighlight({ type: 'StepContextButton', button: 'notes', index, moduleIdName }),
    isOwner: state.workflow.is_owner,
    isReadOnly: state.workflow.read_only,
    isAnonymous: state.workflow.is_anonymous,
    workflowId: state.workflow.id,
    fetchModuleExists: fetchIndex !== null && fetchIndex <= index
  }
}

const mapDispatchToProps = {
  clearNotifications: clearNotificationsAction,
  setSelectedStep: setSelectedStepAction,
  setStepCollapsed: setStepCollapsedAction,
  setStepParams: setStepParamsAction,
  setStepSecret: setStepSecretAction,
  maybeRequestFetch: maybeRequestStepFetchAction,
  applyQuickFix: quickFixAction,
  setStepNotes: setStepNotesAction,
  deleteSecret: deleteSecretAction,
  startCreateSecret: startCreateSecretAction
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(Step)
