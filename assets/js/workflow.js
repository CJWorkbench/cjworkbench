// This is the main script for the Workflow view

import React from 'react'
import ModuleLibrary from './ModuleLibrary'
import { WorkflowNavBar } from './navbar'
import OutputPane from './OutputPane'
import Lesson from './lessons/Lesson'
import PropTypes from 'prop-types'
import ModuleStack from './ModuleStack'
import CustomDragLayer from './CustomDragLayer'

// ---- WorkflowMain ----

class Workflow extends React.Component {

  constructor(props: iProps) {
    super(props);
    this.state = {
        isPublic: false,
        focus: false,
        overlapping: false, // Does the right pane overlap the left pane? Used to set focus, draw shadows, etc
        libraryOpen: false 
    };
    this.setOverlapping = this.setOverlapping.bind(this);
    this.setLibraryOpen = this.setLibraryOpen.bind(this);
  }

  componentWillReceiveProps(nextProps) {

    if (nextProps.workflow === undefined) {
      return false;
    }

    this.setState({
      isPublic: nextProps.workflow.public,
      libraryOpen: (!nextProps.isReadOnly && !nextProps.workflow.module_library_collapsed)
    });
  }

  setOverlapping(overlapping) {
    this.setState({
      overlapping
    });
  }

  setLibraryOpen(libraryOpen, cb) {
    this.setState({
      libraryOpen
    }, cb);
  }

  render() {
    // Wait until we have a workflow to render
    if (this.props.workflow === undefined) {
      return null;
    }

    let selectedWorkflowModuleRef = this.props.workflow.wf_modules.find((wf) => {
      return wf.id === this.props.selected_wf_module;
    });
    return (
        <div className="workflow-root">
          { this.props.lesson ? <Lesson {...this.props.lesson} /> : '' }

          <ModuleLibrary
            addModule={(module_id, placeholder) => this.props.addModule(module_id, this.props.workflow.wf_modules.length, placeholder)}
            dropModule={(module_id, insert_before, placeholder) => this.props.addModule(module_id, ((insert_before === false) ? this.props.workflow.wf_modules.length : insert_before), placeholder)}
            api={this.props.api}
            isReadOnly={this.props.workflow.read_only}
            workflow={this.props.workflow} // We pass the workflow down so that we can toggle the module library visibility in a sensible manner.
            libraryOpen={this.state.libraryOpen}
            setLibraryOpen={this.setLibraryOpen}
          />

          <div className="workflow-container">

            <WorkflowNavBar
              workflow={this.props.workflow}
              api={this.props.api}
              isReadOnly={this.props.workflow.read_only}
              loggedInUser={this.props.loggedInUser}
            />

            <div className={"workflow-columns" + (this.state.overlapping ? " overlapping" : "")}>
              <ModuleStack
                workflow={this.props.workflow}
                selected_wf_module={this.props.selected_wf_module}
                changeParam={this.props.changeParam}
                removeModule={this.props.removeModule}
                addModule={this.props.addModule}
                api={this.props.api}
                loggedInUser={this.props.loggedInUser}
                isOver={this.props.isOver}
                dragItem={this.props.dragItem}
                focus={this.state.focus}
                setFocus={(e) => { this.setState({ focus: true }) }}
              />
              <OutputPane
                id={this.props.selected_wf_module}
                revision={this.props.workflow.revision}
                api={this.props.api}
                htmlOutput={(selectedWorkflowModuleRef && selectedWorkflowModuleRef.html_output)}
                selectedWfModuleId={this.props.selected_wf_module}
                workflow={this.props.workflow}
                focus={!this.state.focus}
                setFocus={(e) => { this.setState({ focus: false }) }}
                libraryOpen={this.state.libraryOpen}
                setOverlapping={this.setOverlapping}
                setLibraryOpen={this.setLibraryOpen}
              />
            </div>
          </div>
          <div className='help-container'>
            <a target="_blank" href="http://help.cjworkbench.org/getting-started/build-your-first-workflow" className=''>
              <div className='help-shortcut btn'>
                <div className='icon-knowledge' />
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
