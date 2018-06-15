// This is the main script for the Workflow view

import React from 'react'
import WorkflowNavBar from './WorkflowNavBar'
import OutputPane from './OutputPane'
import Lesson from './lessons/Lesson'
import PropTypes from 'prop-types'
import ModuleStack from './ModuleStack'
import { logUserEvent } from './utils'

// ---- WorkflowMain ----

class Workflow extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
        isPublic: false,
        isFocusModuleStack: false,
        overlapping: false, // Does the right pane overlap the left pane? Used to set focus, draw shadows, etc
    };
  }

  componentWillReceiveProps(nextProps) {

    if (nextProps.workflow === undefined) {
      return false;
    }

    this.setState({
      isPublic: nextProps.workflow.public,
    });
  }

  setOverlapping = (overlapping) => {
    this.setState({
      overlapping
    });
  }

  setFocusModuleStack = () => {
    this.setState({
      isFocusModuleStack: true,
    });
  }

  setFocusOutputPane = () => {
    this.setState({
      isFocusModuleStack: false,
    });
  }

  render() {
    // Wait until we have a workflow to render
    if (this.props.workflow === undefined) {
      return null;
    }

    const selectedWorkflowModuleRef = this.props.workflow.wf_modules.find((wf) => {
      return wf.id === this.props.selected_wf_module;
    });

    let className = 'workflow-root'
    if (this.props.lesson) {
      className += ' in-lesson'
    }

    return (
        <div className={className}>
          { this.props.lesson ? <Lesson {...this.props.lesson} logUserEvent={logUserEvent} /> : '' }

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
                api={this.props.api}
                loggedInUser={this.props.loggedInUser}
                isOver={this.props.isOver}
                dragItem={this.props.dragItem}
                focus={this.state.isFocusModuleStack}
                setFocus={this.setFocusModuleStack}
              />
              <OutputPane
                id={this.props.selected_wf_module}
                revision={this.props.workflow.revision}
                api={this.props.api}
                htmlOutput={(selectedWorkflowModuleRef && selectedWorkflowModuleRef.html_output)}
                selectedWfModuleId={this.props.selected_wf_module}
                workflow={this.props.workflow}
                focus={!this.state.isFocusModuleStack}
                setFocus={this.setFocusOutputPane}
                setOverlapping={this.setOverlapping}
              />
            </div>
          </div>
          <div className='help-container'>
            <a target="_blank" href="http://help.workbenchdata.com/getting-started/build-your-first-workflow" >
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
  removeModule:       PropTypes.func.isRequired,
  loggedInUser:       PropTypes.object,             // undefined if no one logged in (viewing public wf)
};
