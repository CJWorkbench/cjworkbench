import React from 'react'
import PropTypes from 'prop-types'
import ModuleSearch from './ModuleSearch'
import WfModule from './wfmodule/WfModule'
import WfModuleHeader from './wfmodule/WfModuleHeader'
import debounce from 'lodash/debounce'
import { addModuleAction, moveModuleAction } from './workflow-reducer'
import { scrollTo } from './utils'
import { connect } from 'react-redux';


class ModuleDropSpot extends React.PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    isDraggingModuleAtIndex: PropTypes.number,
    moveModuleByIndex: PropTypes.func.isRequired, // func(oldIndex, newIndex) => undefined
  }

  constructor(props) {
    super(props)

    this.state = {
      isDragHovering: false,
    }
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
    if (!this.canDrop()) return

    this.setState({
      isDragHovering: true,
    })
  }

  onDragLeave = () => {
    if (!this.canDrop()) return

    this.setState({
      isDragHovering: false,
    })
  }

  onDrop = (ev) => {
    if (!this.canDrop()) return

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
  }

  constructor(props) {
    super(props)

    this.state = {
      isSearching: false,
    }
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
        <ModuleSearch onClickModuleId={this.onClickModuleId} onCancel={this.onCancelSearch} />
      )
    } else {
      return null
    }
  }

  render() {
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
  }

  renderModuleSearchButton() {
    let className = 'add-module-in-between-search'
    if (this.state.isSearching) className += ' searching'

    return (
      <div className={className}>
        <button className="search" title="Add Module" onClick={this.onClickSearch}>
          <i className="icon-addc"></i>
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
  }

  renderModuleSearchButton() {
    let className = 'add-module-search'
    if (this.state.isSearching) className += ' searching'

    return (
      <div className={className}>
        <button className="search" onClick={this.onClickSearch}>
          <i className="icon-addc"></i>{' '}
          Add Module
        </button>
        {this.renderModuleSearchIfSearching()}
      </div>
    )
  }
}

const FixmeIKilledDragAndDrop = () => {}

class ModuleStack extends React.Component {
  static propTypes = {
    api:                PropTypes.object.isRequired,
    workflow:           PropTypes.object,
    selected_wf_module: PropTypes.number,
    changeParam:        PropTypes.func.isRequired,
    addModule:          PropTypes.func.isRequired, // func(moduleId, index) => undefined
    moveModuleByIndex:  PropTypes.func.isRequired, // func(oldIndex, newIndex) => undefined
    removeModule:       PropTypes.func.isRequired,
    loggedInUser:       PropTypes.object             // undefined if no one logged in (viewing public wf)
  }

  constructor(props) {
    super(props);
    this.scrollRef = React.createRef();
    // Debounced so that execution is cancelled if we start
    // another animation. See note on focusModule definition.
    this.focusModule = debounce(this.focusModule.bind(this), 200);

    this.state = {
      isDraggingModuleAtIndex: null,
    }
  }

  focusModule(module) {
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
        isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
        addModule={this.props.addModule}
        moveModuleByIndex={this.props.moveModuleByIndex}
        />
    )
  }

  render() {
    const wfModules = this.props.wf_modules

    const spotsAndItems = wfModules.map((item, i) => {
      // If this item is replacing a placeholder, disable the enter animations
      if (item.placeholder) {
        return (
          <React.Fragment key={i}>
            {this.moduleStackInsertSpot(i)}
            <WfModuleHeader
              moduleName={item.name}
              moduleIcon={item.icon}
              focusModule={this.focusModule}
              isSelected={false}
              />
          </React.Fragment>
        )
      } else {
        return (
          <React.Fragment key={i}>
            {this.moduleStackInsertSpot(i)}
            <WfModule
              isReadOnly={this.props.workflow.read_only}
              wfModule={item}
              changeParam={this.props.changeParam}
              removeModule={this.props.removeModule}
              revision={this.props.workflow.revision}
              selected={item.id === this.props.selected_wf_module}
              api={this.props.api}
              user={this.props.loggedInUser}
              loads_data={item.moduleVersion && item.module_version.module.loads_data}
              index={i}
              onDragStart={this.onDragStart}
              onDragEnd={this.onDragEnd}
              focusModule={this.focusModule}
            />
          </React.Fragment>
        )
      }
    })

    return (
      <div className="module-stack">
        {spotsAndItems}
        <LastModuleStackInsertSpot
          key="last"
          index={wfModules.length}
          isDraggingModuleAtIndex={this.state.isDraggingModuleAtIndex}
          addModule={this.props.addModule}
          moveModuleByIndex={this.props.moveModuleByIndex}
      />
      </div>
    )
  }
}

const mapStateToProps = (state) => {
  return {
    wf_modules: state.workflow.wf_modules
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
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(ModuleStack);
