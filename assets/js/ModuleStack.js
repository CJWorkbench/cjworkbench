import React from 'react'
import { getPageID, csrfToken, scrollTo } from './utils'
import { DropTarget } from 'react-dnd'
import FlipMove from 'react-flip-move'
import PropTypes from 'prop-types'
import SortableWfModule from './wfmodule/WfModule'
import WfModuleHeader from './wfmodule/WfModuleHeader'
import WfModulePlaceholder from './wfmodule/WfModulePlaceholder'
import debounce from 'lodash/debounce'
import { store, insertPlaceholderAction } from "./workflow-reducer";
import flow from 'lodash.flow'
import {connect} from 'react-redux';

class ModuleStack extends React.Component {

  constructor(props) {
    super(props);
    this.toggleDrag = this.toggleDrag.bind(this);
    this.scrollRef = null;
    this.setScrollRef = this.setScrollRef.bind(this);
    // Debounced so that execution is cancelled if we start
    // another animation. See note on focusModule definition.
    this.focusModule = debounce(this.focusModule.bind(this), 200);
    this.state = {
      canDrag: true,
      justDropped: false
    }
  }

  toggleDrag() {
    this.setState({ canDrag: !this.state.canDrag });
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
    if (!this.props.wf_modules || this.props.wf_modules.length === 0) {
      return (
        this.props.connectDropTarget(
          <div className={'modulestack-empty mx-auto d-flex align-items-center justify-content-center ' + (this.props.dragItem ? 'dragging' : '')}>
            <span className={'title-3 ml-4 ' + (this.props.dragItem ? 't-d-blue' : 't-orange')}>
              DROP MODULE HERE
            </span>
          </div>
        )
      )
    }

    let enterAnimation = true;
    let exitAnimation = true;
    let listItems = this.props.wf_modules.map(function(item, i) {

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
          isSelected={true}
        />;
      }
      let childProps = {
        'data-isReadOnly': this.props.workflow.read_only,
        'data-wfmodule': item,
        'data-changeParam': this.props.changeParam,
        'data-removeModule': this.props.removeModule,
        'data-revision': this.props.workflow.revision,
        'data-selected': (item.id === this.props.selected_wf_module),
        'data-api': this.props.api,
        'data-user': this.props.loggedInUser,
        loads_data: item.module_version ? item.module_version.module.loads_data : false,
        index: i,
        drag: this.drag,
        dragNew: this.dragNew,
        drop: this.drop,
        key: item.id,
        canDrag: this.state.canDrag,  // governs drag-ability of WfModule - how do we change this from events in <WfParameter>?
        toggleDrag: this.toggleDrag,
        focusModule: this.focusModule,
        setSelectedModuleRef: this.setSelectedModuleRef,
      };

      if (item.insert) {
        return <WfModulePlaceholder {...childProps} />
      }

      return (
        <SortableWfModule
          {...childProps}
        />
      );

    }, this);
    return (
      <div className={ "modulestack" + (this.props.focus ? " focus": "") }
           onClick={ this.props.setFocus } ref={ this.setScrollRef }>
        {this.props.connectDropTarget(
        <div className={"modulestack-list mx-auto " + ((this.props.dragItem && this.props.canDrop) ? 'dragging' : '')}>
          {listItems}

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
    const source = monitor.getItem();
    const target = props.index;
    // Replace this with optimistic updates via redux
    component.setState({
      justDropped:true
    });
    return {
      source,
      target
    }
  },

  hover (props, monitor, component) {
    if (monitor.isOver({shallow: true})) {
      let item = monitor.getItem();
      if (item.index === false) {
        let targetIndex = component.props.workflow.wf_modules.length;
        store.dispatch(insertPlaceholderAction(monitor.getItem(), targetIndex));
        monitor.getItem().index = targetIndex;
      }
    }
  }
};

function targetCollect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    isOver: monitor.isOver(),
    canDrop: monitor.canDrop(),
    dragItem: monitor.getItem()
  }
}

const mapStateToProps = (state) => {
  return {
    wf_modules: state.workflow.wf_modules
  }
};

const mapDispatchToProps = {
  insertPlaceholderAction,
};

export default flow(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  DropTarget('module', targetSpec, targetCollect)
)(ModuleStack);

