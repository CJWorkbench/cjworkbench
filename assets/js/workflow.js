// This is the main script for the Workflow view

import React from 'react'
import { sortable } from 'react-sortable'
import ModuleLibrary from './ModuleLibrary'
import { WorkflowNavBar } from './navbar'
import { SortableWfModule, SortableWfModulePlaceholder } from './WfModule'
import OutputPane from './OutputPane'
import PropTypes from 'prop-types'
import { getPageID, csrfToken } from './utils'
import { DropTarget } from 'react-dnd'
import withScrolling from 'react-dnd-scrollzone'
import FlipMove from 'react-flip-move'
import { OutputIframe } from './OutputIframe'

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

class WorkflowList extends React.Component {

  constructor(props) {
    super(props);
    this.drag = this.drag.bind(this);
    this.dragNew = this.dragNew.bind(this);
    this.dropNew = this.dropNew.bind(this);
    this.drop = this.drop.bind(this);
    this.state = {
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
              DRAG AND DROP MODULE HERE
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

WorkflowList.propTypes = {
  api:                PropTypes.object.isRequired,
  workflow:           PropTypes.object,
  selected_wf_module: PropTypes.number,
  changeParam:        PropTypes.func.isRequired,
  addModule:          PropTypes.func.isRequired,
  removeModule:       PropTypes.func.isRequired,
  loggedInUser:       PropTypes.object             // undefined if no one logged in (viewing public wf)
};

const SortableList = DropTarget('module', targetSpec, targetCollect)(WorkflowList);



// ---- WorkflowMain ----

class Workflow extends React.Component {

  constructor(props: iProps) {
    super(props);
    this.state = {
      isPublic: false
    };
  }

  componentWillReceiveProps(nextProps) {

    if (nextProps.workflow === undefined) {
      return false;
    }

    this.setState({
      isPublic: nextProps.workflow.public
    });
  }

  render() {
    // Wait until we have a workflow to render
    if (this.props.workflow === undefined) {
      return null;
    }

    let selected_workflow_module_ref = this.props.workflow.wf_modules.find((wf) => {
      return wf.id === this.props.selected_wf_module;
    });

    var moduleLibrary = <ModuleLibrary
                          addModule={module_id => this.props.addModule(module_id, this.props.workflow.wf_modules.length)}
                          dropModule={(module_id, insert_before) => this.props.addModule(module_id, (insert_before === false) ? this.props.workflow.wf_modules.length : insert_before)}
                          api={this.props.api}
                          isReadOnly={this.props.workflow.read_only}
                          workflow={this.props.workflow} // We pass the workflow down so that we can toggle the module library visibility in a sensible manner.
                        />

    var navBar =  <WorkflowNavBar
                    workflow={this.props.workflow}
                    api={this.props.api}
                    isReadOnly={this.props.workflow.read_only}
                    loggedInUser={this.props.loggedInUser}
                  />

    var moduleStack = <SortableList
                        workflow={this.props.workflow}
                        selected_wf_module={this.props.selected_wf_module}
                        changeParam={this.props.changeParam}
                        removeModule={this.props.removeModule}
                        addModule={this.props.addModule}
                        api={this.props.api}
                        loggedInUser={this.props.loggedInUser}
                        isOver={this.props.isOver}
                        dragItem={this.props.dragItem}
                      />

    var outputPane =  <OutputPane
                    id={this.props.selected_wf_module}
                    revision={this.props.workflow.revision}
                    api={this.props.api}
                  />


    // Main Layout of Workflow Page:
    // Module Library occupies left-hand bar of page from top to bottom
    // Navbar occupies remaining top bar from edge of ML to right side
    // Module Stack occupies fixed-width colum, right from edge of ML, from bottom of NavBar to end of page
    // Output Pane occupies remaining space in lower-right of page
    //const ScrollingDiv = withScrolling('div');
    const stackContainer = (
      <div className="modulestack">
        {moduleStack}
      </div>
    );
    return (
        <div className="workflow-root">

          {moduleLibrary}

          <div className="workflow-container">

            {navBar}

            <div className="workflow-columns">
              {stackContainer}
              {outputPane}
            </div>

          </div>
          <div className='help-container'>
            <a target="_blank" href="https://intercom.help/tables" className=''>
              <div className='help-shortcut btn'>
                <div className='icon-knowledge'></div>
              </div>
            </a>
          </div>

        </div>
    );
  }
}

export default Workflow;

Workflow.propTypes = {
  api:                PropTypes.object.isRequired,
  workflow:           PropTypes.object,             // not required as fetched after page loads
  selected_wf_module: PropTypes.number,
  changeParam:        PropTypes.func.isRequired,
  addModule:          PropTypes.func.isRequired,
  removeModule:       PropTypes.func.isRequired,
  loggedInUser:       PropTypes.object,             // undefined if no one logged in (viewing public wf)
};
