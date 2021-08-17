// This is the main script for the Workflow view

import React from 'react'
import PropTypes from 'prop-types'
import WorkflowNavBar from './WorkflowNavBar'
import Lesson from './lessons/Lesson'
import WorkflowEditor from './WorkflowEditor'
import { connect } from 'react-redux'
import { setWorkflowNameAction } from './workflow-reducer'
import ShuttingDownPublicSite2021 from './ShuttingDownPublicSite2021'
import selectIsAnonymous from './selectors/selectIsAnonymous'
import selectIsReadOnly from './selectors/selectIsReadOnly'
import { Trans } from '@lingui/macro'

export function MaybeNotYourWorkflow (props) {
  const { isReadOnly, isAnonymous, isLoggedIn } = props
  if (!isReadOnly && !isAnonymous) {
    return <ShuttingDownPublicSite2021 /> // it's your workflow
  }

  return (
    <h3 className='not-your-workflow'>
      <span>
        {isAnonymous
          ? <Trans id='js.Workflow.isAnonymous'>Demo workflow</Trans>
          : <Trans id='js.Workflow.isShared'>You are viewing a shared workflow</Trans>}
      </span>
      <span>{' - '}</span>
      <span>
        {isLoggedIn
          ? (
            <Trans id='js.Workflow.suggestion.duplicateToSaveChanges'>
              Duplicate it to save your changes
            </Trans>
            )
          : (
            <Trans
              id='js.Workflow.suggestion.signInToSaveChanges'
              comment='The tag is a link to the login page'
            >
              <a
                href={`/account/login/?next=/workflows/${props.workflowId}`}
                className='action-button'
              >
                Sign in
              </a>{' '}
              to save your changes
            </Trans>
            )}
      </span>
    </h3>
  )
}

export function Workflow (props) {
  const { api, workflow, lesson, isReadOnly, isAnonymous, loggedInUser, setWorkflowName } = props

  let className = 'workflow-root'
  if (lesson) {
    className += ' in-lesson'
  }
  if (isReadOnly) {
    className += ' read-only'
  }

  return (
    <main className={className}>
      {lesson ? <Lesson {...lesson} /> : null}

      <div className='workflow-container'>
        <WorkflowNavBar
          workflow={workflow}
          lesson={lesson}
          api={api}
          isReadOnly={isReadOnly}
          loggedInUser={loggedInUser}
          setWorkflowName={setWorkflowName}
        />

        <WorkflowEditor api={api} />

        <MaybeNotYourWorkflow
          isLoggedIn={loggedInUser !== null}
          isReadOnly={isReadOnly}
          isAnonymous={isAnonymous}
        />
      </div>
    </main>
  )
}
Workflow.propTypes = {
  api: PropTypes.object.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  isAnonymous: PropTypes.bool.isRequired,
  workflow: PropTypes.object.isRequired,
  setWorkflowName: PropTypes.func.isRequired, // func(newName) => undefined
  lesson: PropTypes.object, // or undefined
  loggedInUser: PropTypes.object // null if no one logged in (viewing public wf)
}

// Handles addStep (and any other actions that change top level workflow state)
const mapStateToProps = state => {
  return {
    workflow: state.workflow,
    loggedInUser: state.loggedInUser,
    isAnonymous: selectIsAnonymous(state),
    isReadOnly: selectIsReadOnly(state)
  }
}

const mapDispatchToProps = {
  setWorkflowName: setWorkflowNameAction
}

export default connect(mapStateToProps, mapDispatchToProps)(Workflow)
