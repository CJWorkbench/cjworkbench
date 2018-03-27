import React from 'react'
import { getPageID, csrfToken, scrollTo } from './utils'
import { DropTarget } from 'react-dnd'
import FlipMove from 'react-flip-move'
import PropTypes from 'prop-types'
import SortableWfModule from './wfmodule/WfModule'
import WfModuleHeader from './wfmodule/WfModuleHeader'
import debounce from 'lodash/debounce'
import { store, insertPlaceholderAction } from "./workflow-reducer";
import flow from 'lodash.flow'
import {connect} from 'react-redux';

class ModuleStack extends React.Component {

  constructor(props) {
    super(props);
    this.startDrag = this.startDrag.bind(this);
    this.stopDrag = this.stopDrag.bind(this);
    this.scrollRef = null;
    this.setScrollRef = this.setScrollRef.bind(this);
    // Debounced so that execution is cancelled if we start
    // another animation. See note on focusModule definition.
    this.focusModule = debounce(this.focusModule.bind(this), 200);
    this.state = {
      canDrag: true
    }
  }

  startDrag() {
    this.setState({ canDrag: true });
  }

  stopDrag() {
    this.setState({ canDrag: false });
  }

  setScrollRef(ref) {
    this.scrollRef = ref;
  }

  focusModule(module) {
    // Wait for the next two browser repaints before animating, because
    // two repaints gets it about right.
    // This is a bad hack that's here because JavaScript doesn't have
    // a global animation queue. We should either find or build one
    // and use it for all of our animations.
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        scrollTo(module, 300, this.scrollRef, this.scrollRef.getBoundingClientRect().height / 3);
      });
    });
  }

  render() {
    let enterAnimation = true;
    let exitAnimation = true;
    let listItems;
    let className;
    if (!this.props.wf_modules || this.props.wf_modules.length === 0) {
      className = 'modulestack-empty ' + (this.props.dragItem ? 'dragging' : '');
      listItems = [
        <div key="empty" className="d-flex align-items-center justify-content-center">
          <span className={'title-3 ml-4 ' + (this.props.dragItem ? 't-d-blue' : 't-orange')}>
            DROP MODULE HERE
          </span>
        </div>
      ];
    } else {
      className = "modulestack" +
        (this.props.focus ? " focus": "") +
        (this.props.isOver ? " over": "") +
        ((this.props.dragItem && this.props.canDrop) ? " dragging" : "");
      listItems = this.props.wf_modules.map(function (item, i) {

        if (item.placeholder) {
          exitAnimation = false;
        }
        if (!item.placeholder && typeof item.pendingId !== 'undefined') {
          enterAnimation = false;
        }

        if (item.placeholder) {
          return <WfModuleHeader
            key={i}
            moduleName={item.name}
            moduleIcon={item.icon}
            focusModule={this.focusModule}
            isSelected={true}/>;
        }
        let childProps = {
          isReadOnly: this.props.workflow.read_only,
          wfModule: item,
          changeParam: this.props.changeParam,
          removeModule: this.props.removeModule,
          revision: this.props.workflow.revision,
          selected: (item.id === this.props.selected_wf_module),
          api: this.props.api,
          user: this.props.loggedInUser,
          loads_data: item.module_version ? item.module_version.module.loads_data : false,
          index: i,
          drag: this.drag,
          dragNew: this.dragNew,
          drop: this.drop,
          key: item.id,
          canDrag: this.state.canDrag,  // governs drag-ability of WfModule - how do we change this from events in <WfParameter>?
          startDrag: this.startDrag,
          stopDrag: this.stopDrag,
          focusModule: this.focusModule,
          setSelectedModuleRef: this.setSelectedModuleRef,
        };

        return (
          <SortableWfModule
            {...childProps}
          />
        );

      }, this);
    }
    return (
      <div className={ className }
           onClick={ this.props.setFocus }
           ref={ this.setScrollRef }>
        {this.props.connectDropTarget(
        <div className="modulestack-list mx-auto">
          <FlipMove duration={100} easing="ease-out" enterAnimation={enterAnimation} leaveAnimation={exitAnimation}>
            {listItems}
          </FlipMove>
        </div>)}
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

// ---- Sortable WfModules within the workflow ----
const targetSpec = {
  drop (props, monitor, component) {
    if (monitor.isOver({shallow: true})) {
      const source = monitor.getItem();
      source.target = component.props.workflow.wf_modules.length;
      return {
        source
      }
    }
  }
  //TODO: Implement a hover function that lets us know if we're at the top of the module stack
};

function targetCollect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    isOver: monitor.isOver({shallow:true}),
    canDrop: monitor.canDrop(),
    dragItem: monitor.getItem()
  }
}

const mapStateToProps = (state) => {
  return {
    wf_modules: state.workflow.wf_modules
  }
};

export default flow(
  connect(
    mapStateToProps,
  ),
  DropTarget('module', targetSpec, targetCollect)
)(ModuleStack);
