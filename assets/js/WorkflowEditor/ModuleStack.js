/* globals HTMLElement */
import React from 'react'
import PropTypes from 'prop-types'
import AddData from './AddData'
import ModuleSearch from './ModuleSearch'
import WfModule from './wfmodule/WfModule'
import WfModuleHeader from './wfmodule/WfModuleHeader'
import { deleteModuleAction, moveModuleAction } from '../workflow-reducer'
import { scrollTo } from '../utils'
import { connect } from 'react-redux'
import lessonSelector from '../lessons/lessonSelector'
import { Trans } from '@lingui/macro'

class ModuleDropSpot extends React.PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    isDraggingModuleAtIndex: PropTypes.number,
    moveModuleByIndex: PropTypes.func.isRequired // func(oldIndex, newIndex) => undefined
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

    this.props.moveModuleByIndex(this.props.isDraggingModuleAtIndex, this.props.index)

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

class ModuleStackInsertSpot extends React.PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    tabSlug: PropTypes.string.isRequired,
    isLast: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    isDraggingModuleAtIndex: PropTypes.number, // or null if not dragging
    moveModuleByIndex: PropTypes.func.isRequired // func(oldIndex, newIndex) => undefined
  }

  renderReadOnly () {
    return (
      <div className='in-between-modules read-only' />
    )
  }

  render () {
    const {
      index, tabSlug, isReadOnly, isLessonHighlight, isLast,
      isDraggingModuleAtIndex, moveModuleByIndex
    } = this.props

    if (isReadOnly) return this.renderReadOnly()

    return (
      <div className='in-between-modules'>
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
          moveModuleByIndex={moveModuleByIndex}
        />
      </div>
    )
  }
}

function EmptyReadOnlyModuleStack () {
  return (
    <div className='empty-read-only'>
      <Trans id='js.WorkflowEditor.ModuleStack.EmptyReadOnlyModuleStack'>This Tab has no Steps.</Trans>
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
function partitionWfModules (wfModules, modules) {
  if (wfModules[0] && modules[wfModules[0].module] && modules[wfModules[0].module].loads_data) {
    return [wfModules[0], wfModules.slice(1)]
  } else {
    return [null, wfModules]
  }
}

export class ModuleStack extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    tabSlug: PropTypes.string,
    selected_wf_module_position: PropTypes.number,
    wfModules: PropTypes.arrayOf(PropTypes.object).isRequired,
    modules: PropTypes.objectOf(PropTypes.shape({ loads_data: PropTypes.bool.isRequired })).isRequired,
    moveModuleByIndex: PropTypes.func.isRequired, // func(tabSlug, oldIndex, newIndex) => undefined
    removeModule: PropTypes.func.isRequired,
    testLessonHighlightIndex: PropTypes.func.isRequired, // func(int) => boolean
    isReadOnly: PropTypes.bool.isRequired,
    /** <WorkflowEditor/Pane> container, where the dialog will open */
    paneRef: PropTypes.shape({ current: PropTypes.instanceOf(HTMLElement) }).isRequired
  }

  // Track state of where we last auto-scrolled.
  // Don't store it in this.state because we never want it to lead to a render
  scrollRef = React.createRef()

  lastScrolledWfModule = { tabSlug: null, index: null } // or { tabSlug, index } pair

  state = {
    isDraggingModuleAtIndex: null,
    zenModeWfModuleId: null
  }

  componentDidUpdate () {
    const tabSlug = this.props.tabSlug
    const index = this.props.selected_wf_module_position

    if (
      tabSlug !== this.lastScrolledWfModule.tabSlug ||
      index !== this.lastScrolledWfModule.index
    ) {
      // We selected a different module. Scroll to it.
      this.lastScrolledWfModule = { tabSlug, index }

      const containerEl = this.scrollRef.current
      const moduleEl = containerEl.querySelectorAll('.wf-module')[index]
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
  setZenMode = (wfModuleId, isZenMode) => {
    const oldId = this.state.zenModeWfModuleId
    if (!isZenMode && wfModuleId === oldId) {
      this.setState({ zenModeWfModuleId: null })
    } else if (isZenMode && oldId === null) {
      this.setState({ zenModeWfModuleId: wfModuleId })
    }
  }

  static getDerivedStateFromProps (props, state) {
    // If we delete a zen-mode while in zen mode, exit zen mode
    const zenId = state.zenModeWfModuleId
    if (zenId && !props.wfModules.find(wfm => wfm.id === zenId)) {
      return { zenModeWfModuleId: null }
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

  moveModuleByIndex = (oldIndex, newIndex) => {
    this.props.moveModuleByIndex(this.props.tabSlug, oldIndex, newIndex)
  }

  render () {
    const { isReadOnly, tabSlug, paneRef, wfModules, modules } = this.props
    const [addDataWfModule, useDataWfModules] = partitionWfModules(wfModules, modules)

    const spotsAndItems = useDataWfModules.map((item, i) => {
      if (addDataWfModule) {
        // We partitioned away wfModules[0] because it'll be an <AddData>
        // component. So increment `i`, setting up the index correctly for
        // each _non-first_ wfModule.
        i += 1
      }

      // If this item is replacing a placeholder, disable the enter animations
      if (!item) {
        return (
          <React.Fragment key={`placeholder-${i}`}>
            <ModuleStackInsertSpot
              index={i}
              tabSlug={this.props.tabSlug}
              isLast={false}
              isReadOnly={this.props.isReadOnly}
              isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
              moveModuleByIndex={this.moveModuleByIndex}
              isLessonHighlight={this.props.testLessonHighlightIndex(i)}
            />
            <WfModuleHeader
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
            <ModuleStackInsertSpot
              index={i}
              tabSlug={this.props.tabSlug}
              isLast={false}
              isReadOnly={this.props.isReadOnly}
              isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
              moveModuleByIndex={this.moveModuleByIndex}
              isLessonHighlight={this.props.testLessonHighlightIndex(i)}
            />
            <WfModule
              isReadOnly={isReadOnly}
              isZenMode={this.state.zenModeWfModuleId === item.id}
              wfModule={item}
              removeModule={this.props.removeModule}
              inputWfModule={i === 0 ? null : wfModules[i - 1]}
              isSelected={i === this.props.selected_wf_module_position}
              isAfterSelected={i > this.props.selected_wf_module_position}
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

    let className = 'module-stack'
    if (this.state.zenModeWfModuleId !== null) className += ' zen-mode'

    return (
      <div className={className} ref={this.scrollRef}>
        {isReadOnly && wfModules.length === 0 ? (
          <EmptyReadOnlyModuleStack />
        ) : (
          <>
            <AddData
              key='add-data'
              tabSlug={tabSlug}
              isLessonHighlight={this.props.testLessonHighlightIndex(0)}
              isReadOnly={this.props.isReadOnly}
              wfModule={addDataWfModule}
              isSelected={!!addDataWfModule && this.props.selected_wf_module_position === 0}
              isZenMode={addDataWfModule && this.state.zenModeWfModuleId === addDataWfModule.id}
              api={this.props.api}
              removeModule={this.props.removeModule}
              setZenMode={this.setZenMode}
              paneRef={paneRef}
            />
            {spotsAndItems}
            {wfModules.length > 0 ? (
              <ModuleStackInsertSpot
                key='last'
                index={wfModules.length}
                tabSlug={tabSlug}
                isLast
                isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
                moveModuleByIndex={this.moveModuleByIndex}
                isLessonHighlight={this.props.testLessonHighlightIndex(wfModules.length)}
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
  const wfModules = tab.wf_module_ids.map(id => state.wfModules[String(id)])
  return {
    workflow: state.workflow,
    selected_wf_module_position: tab.selected_wf_module_position,
    tabSlug,
    wfModules,
    modules,
    isReadOnly: state.workflow.read_only,
    testLessonHighlightIndex: (index) => testHighlight({ type: 'Module', name: null, index: index })
  }
}

const mapDispatchToProps = (dispatch) => {
  return {
    moveModuleByIndex (tabSlug, oldIndex, newIndex) {
      const action = moveModuleAction(tabSlug, oldIndex, newIndex)
      dispatch(action)
    },

    removeModule (wfModuleId) {
      const action = deleteModuleAction(wfModuleId)
      dispatch(action)
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(ModuleStack)
