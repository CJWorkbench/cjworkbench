// This is the main script for the Workflow view

import React from 'react'
import WorkflowNavBar from './WorkflowNavBar'
import OutputPane from './OutputPane'
import Lesson from './lessons/Lesson'
import PropTypes from 'prop-types'
import ModuleStack from './ModuleStack'
import Tabs from './Tabs'
import { logUserEventEvenInLesson } from './utils'
import { connect } from 'react-redux'

export function MaybeNotYourWorkflow(props) {
  if (!props.isReadOnly && !props.isAnonymous) {
    return null // it's your workflow
  }

  const F = React.Fragment

  let suggestion = null
  if (props.isLoggedIn) {
    suggestion = <h3 className="suggestion">Duplicate it to save your changes</h3>
  } else {
    suggestion = <h3 className="suggestion"><a href={`/account/login/?next=/workflows/${props.workflowId}`} className="action-button ">Sign in</a> to save your changes</h3>
  }

  let inner, className
  if (props.isAnonymous) {
    className = 'is-anonymous'
    inner = (
      <F>
        <h3>Demo workflow -</h3>
        <p className="message"></p>
        {suggestion}
      </F>
    )
  } else if (props.isReadOnly) {
    className = 'is-read-only'
    inner = (
      <F>
        <h3>You are viewing a shared workflow</h3>
        <p className="message"></p>
        {suggestion}
      </F>
    )
  }

  return (
    <div className={`not-your-workflow ${className}`}>{inner}</div>
  )
}

// ---- WorkflowMain ----

export class Workflow extends React.PureComponent {
  static propTypes = {
    api:                PropTypes.object.isRequired,
    isReadOnly:         PropTypes.bool.isRequired,
    isAnonymous:        PropTypes.bool.isRequired,
    workflow:           PropTypes.object.isRequired,
    lesson:             PropTypes.object, // or undefined
    loggedInUser:       PropTypes.object,             // undefined if no one logged in (viewing public wf)
  }

  render() {
    const { lesson } = this.props

    let className = 'workflow-root'
    if (this.props.lesson) {
      className += ' in-lesson'
    }
    if (this.props.isReadOnly) {
      className += ' read-only'
    }
    if (this.props.isAnonymous) {
      className += ' anonymous'
    }

    return (
      <div className={className}>
        { lesson ? <Lesson {...lesson} logUserEvent={logUserEventEvenInLesson} /> : null }

        <div className="workflow-container">
          <WorkflowNavBar
            workflow={this.props.workflow}
            lesson={lesson}
            api={this.props.api}
            isReadOnly={this.props.workflow.read_only}
            loggedInUser={this.props.loggedInUser}
          />

          <div className='workflow-columns'>
            <ModuleStack api={this.props.api} />
            <OutputPane api={this.props.api} />
          </div>

          <Tabs />

          <MaybeNotYourWorkflow
            workflowId={this.props.workflow.url_id}
            isLoggedIn={!!this.props.loggedInUser}
            isReadOnly={this.props.isReadOnly}
            isAnonymous={this.props.isAnonymous}
            />
        </div>
      </div>
    )
  }
}

// Handles addModule (and any other actions that change top level workflow state)
const mapStateToProps = (state) => {
  return {
    workflow: state.workflow,
    loggedInUser: state.loggedInUser,
    isAnonymous: state.workflow.is_anonymous,
    isReadOnly: state.workflow.read_only
  }
}

export default connect(
  mapStateToProps
)(Workflow)
