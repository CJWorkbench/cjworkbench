// This is the main script for the Workflow view

import React from 'react'
import { sortable } from 'react-sortable'
import ModuleLibrary from './ModuleLibrary'
import { WorkflowNavBar } from './navbar'
import WfModule from './WfModule'
import OutputPane from './OutputPane'
import PropTypes from 'prop-types'
import { getPageID, csrfToken } from './utils'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'

// ---- Sortable WfModules within the workflow ----
var SortableWfModule = WfModule;

class SortableList extends React.Component {

  constructor(props) {
    super(props);
    this.drag = this.drag.bind(this);
    this.dropNew = this.dropNew.bind(this);
    this.drop = this.drop.bind(this);
    this.state = {
      wf_modules: this.props.data.wf_modules
    }
  }

  drag(sourceIndex, targetIndex) {
    var newArray = this.state.wf_modules.slice(0);
    // pull out the item we want...
    var item = newArray.splice(sourceIndex, 1);

    newArray.splice(targetIndex, 0, ...item);
    this.setState({
      wf_modules: newArray
    });
  }

  dropNew(wfId, moduleId, insertBefore) {
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
    if (nextProps.data.wf_modules !== this.state.wf_modules) {
      this.setState({ wf_modules: nextProps.data.wf_modules });
    }
  }

  render() {
    var listItems = this.state.wf_modules.map(function(item, i) {
      var childProps = {
        'data-isReadOnly': this.props.data.read_only,
        'data-wfmodule': item,
        'data-changeParam': this.props.changeParam,
        'data-removeModule': this.props.removeModule,
        'data-revision': this.props.data.revision,
        'data-selected': (item.id == this.props.selected_wf_module),
        'data-api': this.props.api,
        'data-user': this.props.user,
        index:i,
        drag: this.drag,
        dropNew: this.dropNew,
        drop: this.drop,
        key: item.id,
      }
      return (
        <SortableWfModule
          {...childProps}
        />
      );

    }, this);

    return (
      <div className="list">{listItems}</div>
    )
  }
}

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

    var moduleLibrary = <ModuleLibrary
                          addModule={module_id => this.props.addModule(module_id, this.props.workflow.wf_modules.length)}
                          api={this.props.api}
                          isReadOnly={this.props.workflow.read_only}
                          workflow={this.props.workflow} // We pass the workflow down so that we can toggle the module library visibility in a sensible manner.
                        />

    var navBar =  <WorkflowNavBar
                    workflow={this.props.workflow}
                    api={this.props.api}
                    isReadOnly={this.props.workflow.read_only}
                    user={this.props.user}
                  />



    var moduleStack = <div className='modulestack-empty mx-auto d-flex align-items-center justify-content-center'>
                        <span className='icon-add-orange module-icon'/>
                        <span className='t-orange title-3 ml-4'>
                          ADD DATA MODULE
                        </span>
                      </div>

    if (!!this.props.workflow.wf_modules && !!this.props.workflow.wf_modules.length) {
      moduleStack = <div className="modulestack-list mx-auto">
                      <SortableList
                        data={this.props.workflow}
                        selected_wf_module={this.props.selected_wf_module}
                        changeParam={this.props.changeParam}
                        removeModule={this.props.removeModule}
                        addModule={this.props.addModule}
                        api={this.props.api}
                        user={this.props.user}
                      />
                    </div>
    }

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
    return (
      <DragDropContextProvider backend={HTML5Backend}>

        <div className="workflow-root">

          {moduleLibrary}

          <div className="workflow-container">

            {navBar}

            <div className="workflow-columns">
                <div className="modulestack">
                  {moduleStack}
                </div>
              <div className="outputpane">
                {outputPane}
              </div>

            </div>

          </div>

        </div>

      </DragDropContextProvider>
    );
  }
}

export default Workflow;

Workflow.propTypes = {
  api:                PropTypes.object.isRequired,
  workflow:           PropTypes.object,             // not required as fetched after page loads
  selected_wf_module: PropTypes.number,
  addModule:          PropTypes.func.isRequired,
  removeModule:       PropTypes.func.isRequired,
  user:               PropTypes.object,
  isReadOnly:         PropTypes.bool  // is this an active prop? to cull?
};
