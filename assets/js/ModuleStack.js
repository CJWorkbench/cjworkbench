import React from 'react'
import { getPageID, csrfToken } from './utils'
import { DropTarget } from 'react-dnd'
import FlipMove from 'react-flip-move'
import PropTypes from 'prop-types'
import { SortableWfModule, SortableWfModulePlaceholder } from './WfModule'


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
  }
}

function targetCollect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    isOver: monitor.isOver(),
    canDrop: monitor.canDrop(),
    dragItem: monitor.getItem()
  }
}

class ModuleStack extends React.Component {

  constructor(props) {
    super(props);
    this.drag = this.drag.bind(this);
    this.dragNew = this.dragNew.bind(this);
    this.dropNew = this.dropNew.bind(this);
    this.drop = this.drop.bind(this);
    this.toggleDrag = this.toggleDrag.bind(this);        
    this.state = {
      canDrag: true,
      justDropped: false,
      wf_modules: this.props.workflow.wf_modules // This is dumb, modifying state modifes the original
    }
  }

  drag(sourceIndex, targetIndex) {
    var newArray = this.state.wf_modules.slice(0);
    // pull out the item we want...
    var item = newArray.splice(sourceIndex, 1);
    //Use the spread operator instead of item[0]
    newArray.splice(targetIndex, 0, ...item);
    this.setState({
      wf_modules: newArray
    });
  }

  dragNew(targetIndex, props) {
    var newArray = this.state.wf_modules.slice(0);
    newArray.splice(targetIndex, 0, props);
    this.setState({
      wf_modules: newArray
    });
  }

  dropNew(moduleId, insertBefore) {
    this.props.addModule(moduleId, insertBefore);
  }

  drop() {
    var newOrder = this.state.wf_modules.map( (item, i) => ({id: item.id, order: i}) )

    fetch('/api/workflows/' + getPageID(), {
      method: 'patch',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(newOrder) })
    .catch( (error) => { console.log('Request failed', error); });
  }

  toggleDrag() {
    this.setState({ canDrag: !this.state.canDrag });
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.workflow.revision !== this.props.workflow.revision) { //TODO: Does this ever fire?
      // New wfmodules, update
      this.setState({
        justDropped: false,
        wf_modules: nextProps.workflow.wf_modules
      });
      return;
    }

    // If nothing is being dragged, and the order of wf_modules are different
    if (!nextProps.dragItem
      && (nextProps.workflow.wf_modules !== this.state.wf_modules)) {
      // And we didn't just drop the thing that was being dragged,
      if (this.state.justDropped === false) {
        // Re-set the wf_modules in the list, drag is cancelled
        this.setState({
          wf_modules: nextProps.workflow.wf_modules
        });
      } else {
        // We just dropped something. Re-set the state.
        this.setState({
          justDropped: false
        });
      }
    }
  }

  render() {
    if (!this.state.wf_modules || this.state.wf_modules.length === 0) {
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

    var listItems = this.state.wf_modules.map(function(item, i) {
      var childProps = {
        'data-isReadOnly': this.props.workflow.read_only,
        'data-wfmodule': item,
        'data-changeParam': this.props.changeParam,
        'data-removeModule': this.props.removeModule,
        'data-revision': this.props.workflow.revision,
        'data-selected': (item.id == this.props.selected_wf_module),
        'data-api': this.props.api,
        'data-user': this.props.loggedInUser,
        loads_data: item.module_version ? item.module_version.module.loads_data : false,
        index:i,
        drag: this.drag,
        dragNew: this.dragNew,
        drop: this.drop,
        dropNew: this.dropNew,
        key: item.id,
        canDrag: this.state.canDrag,  // governs drag-ability of WfModule - how do we change this from events in <WfParameter>?
        toggleDrag: this.toggleDrag
      }

      if (item.insert) {
        return <SortableWfModulePlaceholder {...childProps} />
      }

      return (
        <SortableWfModule
          {...childProps}
        />
      );

    }, this);

    return (
      this.props.connectDropTarget(
        <div className={"modulestack-list mx-auto " + ((this.props.dragItem && this.props.canDrop) ? 'dragging' : '')}>
          <FlipMove duration={100} easing="ease-out">
            {listItems}
          </FlipMove>
        </div>
      )
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

export default DropTarget('module', targetSpec, targetCollect)(ModuleStack);
