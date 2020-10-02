/* globals HTMLElement */
import React from 'react'
import PropTypes from 'prop-types'
import AddData from './AddData'
import ModuleSearch from './ModuleSearch'
import Step from './step/Step'
import StepHeader from './step/StepHeader'
import { deleteStepAction, moveStepAction } from '../workflow-reducer'
import { scrollTo } from '../utils'
import { connect } from 'react-redux'
import lessonSelector from '../lessons/lessonSelector'
import { Trans } from '@lingui/macro'

class ModuleDropSpot extends React.PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    isDraggingModuleAtIndex: PropTypes.number,
    moveStepByIndex: PropTypes.func.isRequired // func(oldIndex, newIndex) => undefined
  }

  state = {
    isDragHovering: false
  }

  canDrop () {
    const { index, isDraggingModuleAtIndex } = this.props
    if (isDraggingModuleAtIndex === null) return false

    // Can't drag to before or after ourselves
    return !(index === isDraggingModuleAtIndex || index === isDraggingModuleAtIndex + 1)
  }

  handleDragOver = (ev) => {
    if (!this.canDrop()) return

    ev.preventDefault() // unlike default, this is a valid drop target
  }

  handleDragEnter = (ev) => {
    if (!this.canDrop(ev)) return

    this.setState({
      isDragHovering: true
    })
  }

  handleDragLeave = (ev) => {
    if (!this.canDrop(ev)) return

    this.setState({
      isDragHovering: false
    })
  }

  handleDrop = (ev) => {
    if (!this.canDrop(ev)) return

    ev.preventDefault() // we want no browser defaults

    this.props.moveStepByIndex(this.props.isDraggingModuleAtIndex, this.props.index)

    this.setState({
      isDragHovering: false // otherwise, will stay hovering next drag
    })
  }

  render () {
    if (this.canDrop()) {
      let className = 'module-drop-zone'
      if (this.state.isDragHovering) className += ' is-drag-hovering'
      return (
        <div
          className={className}
          onDragOver={this.handleDragOver}
          onDragEnter={this.handleDragEnter}
          onDragLeave={this.handleDragLeave}
          onDrop={this.handleDrop}
        >
          <div className='highlight'>
            <i className='icon-add' />
          </div>
        </div>

      )
    } else {
      return null
    }
  }
}

class StepListInsertSpot extends React.PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    tabSlug: PropTypes.string.isRequired,
    isLast: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    isDraggingModuleAtIndex: PropTypes.number, // or null if not dragging
    moveStepByIndex: PropTypes.func.isRequired // func(oldIndex, newIndex) => undefined
  }

  renderReadOnly () {
    return (
      <div className='in-between-steps read-only' />
    )
  }

  render () {
    const {
      index, tabSlug, isReadOnly, isLessonHighlight, isLast,
      isDraggingModuleAtIndex, moveStepByIndex
    } = this.props

    if (isReadOnly) return this.renderReadOnly()

    return (
      <div className='in-between-steps'>
        <ModuleSearch
          index={index}
          tabSlug={tabSlug}
          className={isLast ? 'module-search-last' : 'module-search-in-between'}
          isLessonHighlight={isLessonHighlight}
          isLastAddButton={isLast}
        />
        <ModuleDropSpot
          index={index}
          isDraggingModuleAtIndex={isDraggingModuleAtIndex}
          moveStepByIndex={moveStepByIndex}
        />
      </div>
    )
  }
}

function EmptyReadOnlyStepList () {
  return (
    <div className='empty-read-only'>
      <Trans id='js.WorkflowEditor.StepList.EmptyReadOnlyStepList'>This Tab has no Steps.</Trans>
    </div>
  )
}

/**
 * Returns [ addDataStep (or null), useDataSteps (Array) ].
 *
 * The `addDataStep` is guaranteed to have `loads_data: true`. There are no
 * guarantees about the `useDataSteps`.
 *
 * Keep in mind that this distinction is _client-side_. The server does not
 * differentiate: the user may end up with a Tab that has many `usesDataStep`s
 * and no `addDataStep`, and the server will actually try and render that.
 */
function partitionSteps (steps, modules) {
  if (steps[0] && modules[steps[0].module] && modules[steps[0].module].loads_data) {
    return [steps[0], steps.slice(1)]
  } else {
    return [null, steps]
  }
}

export class StepList extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    tabSlug: PropTypes.string,
    selected_step_position: PropTypes.number,
    steps: PropTypes.arrayOf(PropTypes.object).isRequired,
    modules: PropTypes.objectOf(PropTypes.shape({ loads_data: PropTypes.bool.isRequired })).isRequired,
    moveStepByIndex: PropTypes.func.isRequired, // func(tabSlug, oldIndex, newIndex) => undefined
    deleteStep: PropTypes.func.isRequired,
    testLessonHighlightIndex: PropTypes.func.isRequired, // func(int) => boolean
    isReadOnly: PropTypes.bool.isRequired,
    /** <WorkflowEditor/Pane> container, where the dialog will open */
    paneRef: PropTypes.shape({ current: PropTypes.instanceOf(HTMLElement) }).isRequired
  }

  // Track state of where we last auto-scrolled.
  // Don't store it in this.state because we never want it to lead to a render
  scrollRef = React.createRef()

  lastScrolledStep = { tabSlug: null, index: null } // or { tabSlug, index } pair

  state = {
    isDraggingModuleAtIndex: null,
    zenModeStepId: null
  }

  componentDidUpdate () {
    const tabSlug = this.props.tabSlug
    const index = this.props.selected_step_position

    if (
      tabSlug !== this.lastScrolledStep.tabSlug ||
      index !== this.lastScrolledStep.index
    ) {
      // We selected a different module. Scroll to it.
      this.lastScrolledStep = { tabSlug, index }

      const containerEl = this.scrollRef.current
      const moduleEl = containerEl.querySelectorAll('.step')[index]
      if (moduleEl) {
        scrollTo(moduleEl, containerEl, 15, 50)
      }
    }
  }

  /**
   * Sets which module has "Zen mode" (extra size+focus).
   *
   * setZenMode(2, true) // module with ID 2 gets "Zen mode"
   * setZenMode(2, false) // module with ID 2 gets _not_ "Zen mode"
   *
   * Only one module can have Zen mode. When module 2 enters Zen mode, Zen
   * mode is "locked" to module 2: no other modules can set it until module
   * 2 exits Zen mode.
   */
  setZenMode = (stepId, isZenMode) => {
    const oldId = this.state.zenModeStepId
    if (!isZenMode && stepId === oldId) {
      this.setState({ zenModeStepId: null })
    } else if (isZenMode && oldId === null) {
      this.setState({ zenModeStepId: stepId })
    }
  }

  static getDerivedStateFromProps (props, state) {
    // If we delete a zen-mode while in zen mode, exit zen mode
    const zenId = state.zenModeStepId
    if (zenId && !props.steps.find(step => step.id === zenId)) {
      return { zenModeStepId: null }
    } else {
      return null
    }
  }

  handleDragStart = (obj) => {
    this.setState({
      isDraggingModuleAtIndex: obj.index
    })
  }

  handleDragEnd = () => {
    this.setState({
      isDraggingModuleAtIndex: null
    })
  }

  moveStepByIndex = (oldIndex, newIndex) => {
    this.props.moveStepByIndex(this.props.tabSlug, oldIndex, newIndex)
  }

  render () {
    const { isReadOnly, tabSlug, paneRef, steps, modules } = this.props
    const [addDataStep, useDataSteps] = partitionSteps(steps, modules)

    const spotsAndItems = useDataSteps.map((item, i) => {
      if (addDataStep) {
        // We partitioned away steps[0] because it'll be an <AddData>
        // component. So increment `i`, setting up the index correctly for
        // each _non-first_ step.
        i += 1
      }

      // If this item is replacing a placeholder, disable the enter animations
      if (!item) {
        return (
          <React.Fragment key={`placeholder-${i}`}>
            <StepListInsertSpot
              index={i}
              tabSlug={this.props.tabSlug}
              isLast={false}
              isReadOnly={this.props.isReadOnly}
              isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
              moveStepByIndex={this.moveStepByIndex}
              isLessonHighlight={this.props.testLessonHighlightIndex(i)}
            />
            <StepHeader
              tabSlug={this.props.tabSlug}
              moduleName=''
              moduleIcon=''
              isSelected={false}
            />
          </React.Fragment>
        )
      } else {
        return (
          <React.Fragment key={`module-${item.id}`}>
            <StepListInsertSpot
              index={i}
              tabSlug={this.props.tabSlug}
              isLast={false}
              isReadOnly={this.props.isReadOnly}
              isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
              moveStepByIndex={this.moveStepByIndex}
              isLessonHighlight={this.props.testLessonHighlightIndex(i)}
            />
            <Step
              isReadOnly={isReadOnly}
              isZenMode={this.state.zenModeStepId === item.id}
              step={item}
              deleteStep={this.props.deleteStep}
              inputStep={i === 0 ? null : steps[i - 1]}
              isSelected={i === this.props.selected_step_position}
              isAfterSelected={i > this.props.selected_step_position}
              api={this.props.api}
              index={i}
              setZenMode={this.setZenMode}
              onDragStart={this.handleDragStart}
              onDragEnd={this.handleDragEnd}
            />
          </React.Fragment>
        )
      }
    })

    let className = 'step-list'
    if (this.state.zenModeStepId !== null) className += ' zen-mode'

    return (
      <div className={className} ref={this.scrollRef}>
        {isReadOnly && steps.length === 0 ? (
          <EmptyReadOnlyStepList />
        ) : (
          <>
            <AddData
              key='add-data'
              tabSlug={tabSlug}
              isLessonHighlight={this.props.testLessonHighlightIndex(0)}
              isReadOnly={this.props.isReadOnly}
              step={addDataStep}
              isSelected={!!addDataStep && this.props.selected_step_position === 0}
              isZenMode={addDataStep && this.state.zenModeStepId === addDataStep.id}
              api={this.props.api}
              deleteStep={this.props.deleteStep}
              setZenMode={this.setZenMode}
              paneRef={paneRef}
            />
            {spotsAndItems}
            {steps.length > 0 ? (
              <StepListInsertSpot
                key='last'
                index={steps.length}
                tabSlug={tabSlug}
                isLast
                isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
                moveStepByIndex={this.moveStepByIndex}
                isLessonHighlight={this.props.testLessonHighlightIndex(steps.length)}
                isReadOnly={this.props.isReadOnly}
              />
            ) : null}
          </>
        )}
      </div>
    )
  }
}

const mapStateToProps = (state) => {
  const { modules } = state
  const { testHighlight } = lessonSelector(state)
  const tabPosition = state.workflow.selected_tab_position
  const tabSlug = state.workflow.tab_slugs[tabPosition]
  const tab = state.tabs[tabSlug]
  const steps = tab.step_ids.map(id => state.steps[String(id)])
  return {
    workflow: state.workflow,
    selected_step_position: tab.selected_step_position,
    tabSlug,
    steps,
    modules,
    isReadOnly: state.workflow.read_only,
    testLessonHighlightIndex: (index) => testHighlight({ type: 'Module', id_name: null, index: index })
  }
}

const mapDispatchToProps = (dispatch) => {
  return {
    moveStepByIndex (tabSlug, oldIndex, newIndex) {
      const action = moveStepAction(tabSlug, oldIndex, newIndex)
      dispatch(action)
    },

    deleteStep (stepId) {
      const action = deleteStepAction(stepId)
      dispatch(action)
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(StepList)
