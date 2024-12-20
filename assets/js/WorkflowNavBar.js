import { Component } from 'react'
import PropTypes from 'prop-types'
import WfHamburgerMenu from './WfHamburgerMenu'
import UndoRedoButtons from './UndoRedoButtons'
import EditableWorkflowName from './EditableWorkflowName'
import { goToUrl, timeDifference } from './utils'
import ShareButton from './ShareModal/ShareButton'
import { i18n } from '@lingui/core'
import { Trans } from '@lingui/macro'

function NoOp () {}

function LessonCourse ({ localeId, course }) {
  let path
  let title

  if (course) {
    path = `/courses/${course.localeId}/${course.slug}`
    title = course.title
  } else {
    path = `/lessons/${localeId}`
    title = (
      <Trans id='js.WorkflowNavBar.LessonCourse.Lesson.title'>Workbench basics</Trans>
    )
  }

  return (
    <div className='course'>
      <a href={path}>{title}</a>
    </div>
  )
}

function LessonWorkflowTitle ({ lesson }) {
  return (
    <div className='title-metadata-stack'>
      <LessonCourse localeId={lesson.localeId} course={lesson.course} />
      <EditableWorkflowName
        value={lesson.header.title}
        onSubmit={NoOp}
        isReadOnly
      />
    </div>
  )
}

function OwnedWorkflowTitleAndMetadata ({ isReadOnly, isAnonymous, workflow, setWorkflowName }) {
  const owner = workflow.owner_name.trim()
  const timeAgo = timeDifference(workflow.last_update, new Date(), i18n)
  return (
    <div className='title-metadata-stack'>
      <EditableWorkflowName value={workflow.name} isReadOnly={isReadOnly} onSubmit={setWorkflowName} />
      <ul className='metadata-container'>
        {isAnonymous
          ? null
          : (
            <li className='attribution'>
              <span className='metadata'>
                <Trans id='js.WorkflowNavBar.OwnedWorkflowTitleAndMetadata.owner'>
                  by {owner}
                </Trans>{' '}
              </span>
              <span className='separator'>-</span>
            </li>
            )}
        <li>
          <Trans
            id='js.WorkflowNavBar.OwnedWorkflowTitleAndMetadata.lastUpdated'
            comment="{timeAgo} will contain something like '4h ago'"
          >
            Updated {timeAgo}
          </Trans>
        </li>
        {!isReadOnly && !isAnonymous
          ? (
            <li>
              <span className='separator'>-</span>
              <ShareButton>
                {workflow.public
                  ? <Trans id='js.WorkflowNavBar.OwnedWorkflowTitleAndMetadata.visibility.public'>Public</Trans>
                  : <Trans id='js.WorkflowNavBar.OwnedWorkflowTitleAndMetadata.visibility.private'>Private</Trans>}
              </ShareButton>
            </li>
            )
          : null}
      </ul>
    </div>
  )
}

function WorkflowTitleAndMetadata ({ lesson, isReadOnly, isAnonymous, workflow, setWorkflowName }) {
  if (lesson) {
    return <LessonWorkflowTitle lesson={lesson} />
  } else {
    return (
      <OwnedWorkflowTitleAndMetadata
        isAnonymous={isAnonymous}
        isReadOnly={isReadOnly}
        workflow={workflow}
        setWorkflowName={setWorkflowName}
      />
    )
  }
}

export default class WorkflowNavBar extends Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    workflow: PropTypes.object.isRequired,
    lesson: PropTypes.shape({
      course: PropTypes.shape({
        slug: PropTypes.string.isRequired,
        title: PropTypes.string.isRequired
      }), // optional -- no course means plain lesson
      header: PropTypes.shape({
        title: PropTypes.string.isRequired
      }).isRequired
    }), // optional -- no lesson means we're not in the "lessons" interface
    isReadOnly: PropTypes.bool.isRequired,
    loggedInUser: PropTypes.object, // null if no user logged in
    setWorkflowName: PropTypes.func.isRequired // func(newName) => undefined
  }

  state = {
    spinnerVisible: false,
    isShareModalOpen: false
  }

  componentWillUnmount = () => {
    this.unmounted = true
  }

  undoRedo (verb) {
    // TODO use reducer for this, with a global "can't tell what's going to
    // change" flag instead of this.state.spinnerVisible.

    // Prevent keyboard shortcuts or mouse double-undoing.
    if (this.state.spinnerVisible) return

    this.setState({ spinnerVisible: true })
    this.props.api[verb](this.props.workflow.id).then(() => {
      if (this.unmounted) return
      this.setState({ spinnerVisible: false })
    })
  }

  undo = () => {
    this.undoRedo('undo')
  }

  redo = () => {
    this.undoRedo('redo')
  }

  handleDuplicate = () => {
    if (!this.props.loggedInUser) {
      // user is NOT logged in, so navigate to sign in
      goToUrl('/account/login')
    } else {
      // user IS logged in: start spinner, make duplicate & navigate there
      this.setState({ spinnerVisible: true })

      this.props.api.duplicateWorkflow(this.props.workflow.id).then(json => {
        goToUrl('/workflows/' + json.id)
      })
    }
  }

  render () {
    const { api, isReadOnly, loggedInUser, lesson, workflow, setWorkflowName } = this.props

    const spinner = this.state.spinnerVisible
      ? (
        <div className='spinner-container'>
          <div className='spinner-l1'>
            <div className='spinner-l2'>
              <div className='spinner-l3' />
            </div>
          </div>
        </div>
        )
      : null

    return (
      <>
        {spinner}
        <nav className='navbar'>
          <div className='navbar-elements'>
            <a href='/workflows/' className='logo-navbar'>
              <img
                className='image'
                src={`${window.STATIC_URL}images/logo.svg`}
              />
            </a>
            <WorkflowTitleAndMetadata
              lesson={lesson}
              isReadOnly={isReadOnly}
              workflow={workflow}
              setWorkflowName={setWorkflowName}
            />
            <div className='nav-buttons'>
              {isReadOnly
                ? null
                : <UndoRedoButtons undo={this.undo} redo={this.redo} />}
              <button name='duplicate' onClick={this.handleDuplicate}>
                <Trans id='js.WorkflowNavBar.duplicate.button'>Duplicate</Trans>
              </button>
              {lesson
                ? null // We haven't yet designed what it means to share a lesson workflow
                : <ShareButton><Trans id='js.WorkflowNavBar.share.shareButton'>Share</Trans></ShareButton>}
              {loggedInUser
                ? <WfHamburgerMenu api={api} user={loggedInUser} />
                : (
                  <a href='/account/login' className='nav--link'>
                    <Trans id='js.WorkflowNavBar.signIn.accountLink'>Sign in</Trans>
                  </a>)}
            </div>
          </div>
        </nav>
      </>
    )
  }
}
