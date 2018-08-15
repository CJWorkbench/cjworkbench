import React from 'react'
import PropTypes from 'prop-types'
import ModuleSearch from './ModuleSearch'
import WfModule from './wfmodule/WfModule'
import WfModuleHeader from './wfmodule/WfModuleHeader'
import debounce from 'lodash/debounce'
import { addModuleAction, deleteModuleAction, moveModuleAction } from './workflow-reducer'
import { scrollTo } from './utils'
import { connect } from 'react-redux';
import lessonSelector from './lessons/lessonSelector'


class ModuleDropSpot extends React.PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    isDraggingModuleAtIndex: PropTypes.number,
    moveModuleByIndex: PropTypes.func.isRequired, // func(oldIndex, newIndex) => undefined
  }

  state = {
    isDragHovering: false
  }

  canDrop() {
    const { index, isDraggingModuleAtIndex } = this.props
    if (isDraggingModuleAtIndex === null) return false

    // Can't drag to before or after ourselves
    return !(index === isDraggingModuleAtIndex || index === isDraggingModuleAtIndex + 1)
  }

  onDragOver = (ev) => {
    if (!this.canDrop()) return

    ev.preventDefault() // unlike default, this is a valid drop target
  }

  onDragEnter = (ev) => {
    if (!this.canDrop(ev)) return

    this.setState({
      isDragHovering: true,
    })
  }

  onDragLeave = (ev) => {
    if (!this.canDrop(ev)) return

    this.setState({
      isDragHovering: false,
    })
  }

  onDrop = (ev) => {
    if (!this.canDrop(ev)) return

    ev.preventDefault() // we want no browser defaults

    this.props.moveModuleByIndex(this.props.isDraggingModuleAtIndex, this.props.index)

    this.setState({
      isDragHovering: false, // otherwise, will stay hovering next drag
    })
  }

  render() {
    if (this.canDrop()) {
      let className = 'module-drop-target'
      if (this.state.isDragHovering) className += ' is-drag-hovering'
      return (
        <div
          className={className}
          onDragOver={this.onDragOver}
          onDragEnter={this.onDragEnter}
          onDragLeave={this.onDragLeave}
          onDrop={this.onDrop}
          ></div>
      )
    } else {
      return null
    }
  }
}


class BaseModuleStackInsertSpot extends React.PureComponent {
  static propTypes = {
    addModule: PropTypes.func.isRequired,
    index: PropTypes.number.isRequired,
    isDraggingModuleAtIndex: PropTypes.number, // or null if not dragging
    moveModuleByIndex: PropTypes.func.isRequired, // func(oldIndex, newIndex) => undefined
    isReadOnly: PropTypes.bool.isRequired
  }

  state = {
    isSearching: false
  }

  onClickSearch = () => {
    this.setState({
      isSearching: true,
    })
  }

  onCancelSearch = () => {
    this.setState({
      isSearching: false,
    })
  }

  onClickModuleId = (moduleId) => {
    this.setState({
      isSearching: false,
    })
    this.props.addModule(moduleId, this.props.index)
  }

  renderModuleSearchButton() {
    throw new Error('Not implemented. Please extend this class.')
  }

  renderModuleSearchIfSearching() {
    if (this.state.isSearching) {
      return (
        <ModuleSearch
          index={this.props.index}
          onClickModuleId={this.onClickModuleId}
          onCancel={this.onCancelSearch}
          />
      )
    } else {
      return null
    }
  }

  renderReadOnly() {
    return (
      <div className="in-between-modules read-only"></div>
    )
  }

  render() {
    if (this.props.isReadOnly) return this.renderReadOnly()

    return (
      <div className="in-between-modules">
        {this.renderModuleSearchButton()}
        <ModuleDropSpot
          index={this.props.index}
          isDraggingModuleAtIndex={this.props.isDraggingModuleAtIndex}
          moveModuleByIndex={this.props.moveModuleByIndex}
          />
      </div>
    )
  }
}

class ModuleStackInsertSpot extends BaseModuleStackInsertSpot {
  static propTypes = {
    addModule: PropTypes.func.isRequired,
    index: PropTypes.number.isRequired,
    isDraggingModuleAtIndex: PropTypes.number, // or null if not dragging
    moveModuleByIndex: PropTypes.func.isRequired, // func(oldIndex, newIndex) => undefined
    isLessonHighlightSearch: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
  }

  renderModuleSearchButton() {
    let className = 'add-module-in-between-search'
    if (this.state.isSearching) className += ' searching'
    if (this.props.isLessonHighlightSearch) className += ' lesson-highlight'

    return (
      <div className={className}>
        <button className="search" title="Add Module" onClick={this.onClickSearch}>
          <i className="icon-add"></i>
        </button>
        {this.renderModuleSearchIfSearching()}
      </div>
    )
  }
}

class LastModuleStackInsertSpot extends BaseModuleStackInsertSpot {
  static propTypes = {
    addModule: PropTypes.func.isRequired,
    index: PropTypes.number.isRequired,
    isDraggingModuleAtIndex: PropTypes.number, // or null if not dragging
    moveModuleByIndex: PropTypes.func.isRequired, // func(oldIndex, newIndex) => undefined
    isLessonHighlightSearch: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
  }

  renderModuleSearchButton() {
    let className = 'add-module-search'
    if (this.state.isSearching) className += ' searching'
    if (this.props.isLessonHighlightSearch) className += ' lesson-highlight'

    return (
      <div className={className}>
        <button className="search" onClick={this.onClickSearch}>
          <i className="icon-addc"></i>{' '}
          <span>Add Module</span>
        </button>
        {this.renderModuleSearchIfSearching()}
      </div>
    )
  }
}

class ModuleStack extends React.Component {
  static propTypes = {
    api:                PropTypes.object.isRequired,
    workflow:           PropTypes.object,
    selected_wf_module: PropTypes.number,
    wfModules:          PropTypes.arrayOf(PropTypes.object).isRequired,
    addModule:          PropTypes.func.isRequired, // func(moduleId, index) => undefined
    moveModuleByIndex:  PropTypes.func.isRequired, // func(oldIndex, newIndex) => undefined
    removeModule:       PropTypes.func.isRequired,
    testLessonHighlightIndex: PropTypes.func.isRequired, // func(int) => boolean
    isReadOnly:         PropTypes.bool.isRequired,
  }

  constructor(props) {
    super(props)

    this.scrollRef = React.createRef()
    // Debounced so that execution is cancelled if we start
    // another animation. See note on focusModule definition.
    this.focusModule = debounce(this.focusModule.bind(this), 200)

    this.state = {
      isDraggingModuleAtIndex: null,
      zenModeWfModuleId: null
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

  static getDerivedStateFromProps(props, state) {
    // If we delete a zen-mode while in zen mode, exit zen mode
    const zenId = state.zenModeWfModuleId
    if (zenId && !props.workflow.wf_modules.includes(zenId)) {
      return { zenModeWfModuleId: null }
    } else {
      return null
    }
  }

  focusModule = (module) => {
    // Wait for the next two browser repaints before animating, because
    // two repaints gets it about right.
    // This is a bad hack that's here because JavaScript doesn't have
    // a global animation queue. We should either find or build one
    // and use it for all of our animations.
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        const ref = this.scrollRef.current
        if (ref) {
          scrollTo(module, 300, ref, ref.getBoundingClientRect().height / 3);
        }
      });
    });
  }

  onDragStart = (obj) => {
    this.setState({
      isDraggingModuleAtIndex: obj.index,
    })
  }

  onDragEnd = () => {
    this.setState({
      isDraggingModuleAtIndex: null,
    })
  }

  moduleStackInsertSpot(index) {
    return (
      <ModuleStackInsertSpot
        index={index}
        isReadOnly={this.props.isReadOnly}
        isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
        addModule={this.props.addModule}
        moveModuleByIndex={this.props.moveModuleByIndex}
        isLessonHighlightSearch={this.props.testLessonHighlightIndex(index)}
        />
    )
  }

  render() {
    const wfModules = this.props.wfModules

    const spotsAndItems = wfModules.map((item, i) => {
      // If this item is replacing a placeholder, disable the enter animations
      if (!item) {
        return (
          <React.Fragment key={`placeholder-${i}`}>
            {this.moduleStackInsertSpot(i)}
            <WfModuleHeader
              moduleName={''/*item.name*/}
              moduleIcon={''/*item.icon*/}
              focusModule={this.focusModule}
              isSelected={false}
              />
          </React.Fragment>
        )
      } else {
        return (
          <React.Fragment key={`module-${item.id}`}>
            {this.moduleStackInsertSpot(i)}
            <WfModule
              isReadOnly={this.props.workflow.read_only}
              isZenMode={this.state.zenModeWfModuleId === item.id}
              wfModule={item}
              removeModule={this.props.removeModule}
              inputWfModule={i === 0 ? null : wfModules[i - 1]}
              selected={i === this.props.selected_wf_module}
              api={this.props.api}
              index={i}
              setZenMode={this.setZenMode}
              onDragStart={this.onDragStart}
              onDragEnd={this.onDragEnd}
              focusModule={this.focusModule}
            />
          </React.Fragment>
        )
      }
    })

    let className = 'module-stack'
    if (this.state.zenModeWfModuleId !== null) className += ' zen-mode'

    return (
      <div className={className}>
        {spotsAndItems}
        <LastModuleStackInsertSpot
          key="last"
          index={wfModules.length}
          isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
          addModule={this.props.addModule}
          moveModuleByIndex={this.props.moveModuleByIndex}
          isLessonHighlightSearch={this.props.testLessonHighlightIndex(wfModules.length)}
          isReadOnly={this.props.isReadOnly}
          />
      </div>
    )
  }
}

const mapStateToProps = (state) => {
  const { testHighlight } = lessonSelector(state)
  return {
    workflow: state.workflow,
    selected_wf_module: state.selected_wf_module,
    wfModules: state.workflow.wf_modules.map(id => state.wfModules[String(id)]),
    isReadOnly: state.workflow.read_only,
    testLessonHighlightIndex: (index) => testHighlight({ type: 'Module', name: null, index: index }),
  }
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    addModule(moduleId, index) {
      const action = addModuleAction(moduleId, index)
      dispatch(action)
    },

    moveModuleByIndex(oldIndex, newIndex) {
      const action = moveModuleAction(oldIndex, newIndex)
      dispatch(action)
    },

    removeModule(wfModuleId) {
      const action = deleteModuleAction(wfModuleId)
      dispatch(action)
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(ModuleStack);
