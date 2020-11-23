/* globals HTMLElement */
import React from 'react'
import PropTypes from 'prop-types'
import AddData from '../AddData'
import Step from '../step/Step'
import StepHeader from '../step/StepHeader'
import StepListInsertSpot from './StepListInsertSpot'
import { scrollTo } from '../../utils'
import { Trans } from '@lingui/macro'

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

export default class StepList extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    tabSlug: PropTypes.string,
    selected_step_position: PropTypes.number,
    steps: PropTypes.arrayOf(PropTypes.object).isRequired,
    modules: PropTypes.objectOf(PropTypes.shape({ loads_data: PropTypes.bool.isRequired })).isRequired,
    reorderStep: PropTypes.func.isRequired, // func(tabSlug, oldIndex, newIndex) => undefined
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
    draggedStep: null,
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
      draggedStep: obj
    })
  }

  handleDragEnd = () => {
    this.setState({
      draggedStep: null
    })
  }

  reorderStep = (...args) => {
    this.setState({
      draggedStep: null
    })
    this.props.reorderStep(...args)
  }

  render () {
    const { isReadOnly, tabSlug, paneRef, steps, modules } = this.props
    const { draggedStep, zenModeStepId } = this.state
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
              tabSlug={tabSlug}
              isLast={false}
              isReadOnly={isReadOnly}
              draggedStep={draggedStep}
              reorderStep={this.reorderStep}
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
              tabSlug={tabSlug}
              isLast={false}
              isReadOnly={isReadOnly}
              draggedStep={draggedStep}
              reorderStep={this.reorderStep}
              isLessonHighlight={this.props.testLessonHighlightIndex(i)}
            />
            <Step
              isReadOnly={isReadOnly}
              isZenMode={zenModeStepId === item.id}
              isDragging={draggedStep ? draggedStep.slug === item.slug : false}
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
    if (zenModeStepId !== null) className += ' zen-mode'

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
              isZenMode={addDataStep && zenModeStepId === addDataStep.id}
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
                draggedStep={draggedStep}
                reorderStep={this.reorderStep}
                isLessonHighlight={this.props.testLessonHighlightIndex(steps.length)}
                isReadOnly={isReadOnly}
              />
            ) : null}
          </>
        )}
      </div>
    )
  }
}
