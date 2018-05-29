import React from 'react'
import PropTypes from 'prop-types'
import ModuleSearch from './ModuleSearch'
import WfModule from './wfmodule/WfModule'
import WfModuleHeader from './wfmodule/WfModuleHeader'
import debounce from 'lodash/debounce'
import { addModuleAction } from './workflow-reducer'
import { scrollTo } from './utils'
import { connect } from 'react-redux';

class BaseModuleStackInsertSpot extends React.PureComponent {
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
    // TODO let people drop-to-reorder here
    return (
      <React.Fragment>
        <div className="module-drop-spot"></div>
        {this.renderModuleSearchButton()}
      </React.Fragment>
    )
  }
}
BaseModuleStackInsertSpot.propTypes = {
  addModule: PropTypes.func.isRequired,
  index: PropTypes.number.isRequired,
}

class ModuleStackInsertSpot extends BaseModuleStackInsertSpot {
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
ModuleStackInsertSpot.propTypes = {
  addModule: PropTypes.func.isRequired,
  index: PropTypes.number.isRequired,
}

class LastModuleStackInsertSpot extends BaseModuleStackInsertSpot {
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
LastModuleStackInsertSpot.propTypes = {
  addModule: PropTypes.func.isRequired,
  index: PropTypes.number.isRequired,
}

const FixmeIKilledDragAndDrop = () => {}

class ModuleStack extends React.Component {
  constructor(props) {
    super(props);
    this.scrollRef = React.createRef();
    // Debounced so that execution is cancelled if we start
    // another animation. See note on focusModule definition.
    this.focusModule = debounce(this.focusModule.bind(this), 200);
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

  addModule = (moduleId, index) => {
    this.props.addModule(moduleId, index)
  }

  render() {
    const wfModules = this.props.wf_modules

    const spotsAndItems = wfModules.map((item, i) => {
      // If this item is replacing a placeholder, disable the enter animations
      if (item.placeholder) {
        return (
          <React.Fragment key={i}>
            <ModuleStackInsertSpot index={i} addModule={this.addModule} />
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
            <ModuleStackInsertSpot index={i} addModule={this.addModule} />
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
              drag={FixmeIKilledDragAndDrop}
              drop={FixmeIKilledDragAndDrop}
              dragNew={FixmeIKilledDragAndDrop}
              canDrag={false}
              startDrag={FixmeIKilledDragAndDrop}
              stopDrag={FixmeIKilledDragAndDrop}
              focusModule={this.focusModule}
            />
          </React.Fragment>
        )
      }
    })

    return (
      <div className="module-stack">
        {spotsAndItems}
        <LastModuleStackInsertSpot key="last" index={wfModules.length} addModule={this.addModule} />
      </div>
    )
  }
}

ModuleStack.propTypes = {
  api:                PropTypes.object.isRequired,
  workflow:           PropTypes.object,
  selected_wf_module: PropTypes.number,
  changeParam:        PropTypes.func.isRequired,
  addModule:          PropTypes.func.isRequired,
  removeModule:       PropTypes.func.isRequired,
  loggedInUser:       PropTypes.object             // undefined if no one logged in (viewing public wf)
};

const mapStateToProps = (state) => {
  return {
    wf_modules: state.workflow.wf_modules
  }
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    addModule: (moduleId, index) => {
      const action = addModuleAction(moduleId, index)
      dispatch(action)
    }
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(ModuleStack);
