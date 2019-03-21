// Elements of /workflows. Navbar plus a list

import React from 'react'
import Navbar from './Navbar'
import PropTypes from 'prop-types'
import ShareModal from '../ShareModal/ModalLoader' // _not_ the Redux-connected component, 'ShareModal'
import { logUserEvent } from '../utils'
import CreateWorkflowButton from './CreateWorkflowButton'
import WorkflowLists from './WorkflowLists'
import { WorkflowListPropType } from './WorkflowList'

export default class Workflows extends React.Component {
  static propTypes = {
    api: PropTypes.shape({
      deleteWorkflow: PropTypes.func.isRequired, // func(id) => Promise[null]
      duplicateWorkflow: PropTypes.func.isRequired // func(id) => Promise[{ id, name }]
    }).isRequired,
    workflows: PropTypes.shape({
      owned: WorkflowListPropType.isRequired,
      shared: WorkflowListPropType.isRequired,
      templates: WorkflowListPropType.isRequired
    }).isRequired,
    user: PropTypes.shape({ id: PropTypes.number.isRequired }) // null/undefined if logged out
  }

  state = {
    workflows: this.props.workflows, // we'll be editing this
    shareModalWorkflowId: null
  }

  get allWorkflows () {
    const { workflows } = this.state
    return [].concat(...Object.keys(workflows).map(k => workflows[k]))
  }

  workflowIdToTabName = (workflowId) => {
    const { workflows } = this.state
    for (const tab in workflows) {
      if (workflows[tab].findIndex(w => w.id === workflowId) !== -1) return tab
    }
    return null
  }

  openShareModal = (workflowId) => {
    this.setState({ shareModalWorkflowId: workflowId })
  }

  closeShareModal = () => {
    this.setState({ shareModalWorkflowId: null })
  }

  logShare = (type) => {
    logUserEvent('Share workflow ' + type)
  }

  renderShareModal = () => {
    const { api } = this.props
    const { shareModalWorkflowId } = this.state

    if (shareModalWorkflowId === null) return null

    const workflow = this.allWorkflows.find(w => w.id === shareModalWorkflowId)
    if (!workflow) return null

    const url = `${window.origin}/workflows/${workflow.id}`

    return (
      <ShareModal
        api={api}
        url={url}
        ownerEmail={workflow.owner_email}
        workflowId={workflow.id}
        isReadOnly={!workflow.is_owner}
        isPublic={workflow.public}
        onChangeIsPublic={this.setIsPublicFromShareModal}
        logShare={this.logShare}
        onClickClose={this.closeShareModal}
      />
    )
  }

  // Ask the user if they really wanna do this. If sure, post DELETE to server
  deleteWorkflow = (workflowId) => {
    const tabName = this.workflowIdToTabName(workflowId)
    if (!tabName) return

    if (!confirm("Permanently delete this workflow?")) return

    this.props.api.deleteWorkflow(workflowId)
      .then(() => {
        this.setState({ workflows: {
          ...this.state.workflows,
          [tabName]: this.state.workflows[tabName].filter(w => w.id !== workflowId)
        }})
      })
  }

  duplicateWorkflow = (id) => {
    return this.props.api.duplicateWorkflow(id)
      .then(json => {
        // Add to beginning of owned list then set activeTab to owned
        this.setState({ workflows: {
          ...this.state.workflows,
          owned: [ json, ...this.state.workflows.owned ]
        }})
      })
  }

  setIsPublicFromShareModal = (isPublic) => {
    const workflowId = this.state.shareModalWorkflowId

    const { workflows } = this.state

    const category = Object.keys(workflows)
      .find(k => workflows[k].findIndex(w => w.id === workflowId) !== -1)

    const newWorkflows = {
      ...workflows,
      [category]: workflows[category].map(w => w.id === workflowId ? { ...w, public: isPublic } : w)
    }

    this.setState({ workflows: newWorkflows })

    this.props.api.setWorkflowPublic(workflowId, isPublic)
  }

  render () {
    const { activeTab, comparator, workflows } = this.state
    const { user } = this.props

    return (
      <div className='workflows-page'>
        <Navbar user={user} />
        <a href='/lessons/' className='lesson-banner mx-auto'>
          <div>
            <div className='content-1'>NEW</div>
            <div className='d-flex'>
              <span className='icon-star'></span>
              <div className=' title-1 '>TRAINING</div>
            </div>
          </div>
          <p>Learn how to work with data without coding</p>
        </a>
        <CreateWorkflowButton>
          Create Workflow
        </CreateWorkflowButton>
        <WorkflowLists
          workflows={workflows}
          deleteWorkflow={this.deleteWorkflow}
          duplicateWorkflow={this.duplicateWorkflow}
          openShareModal={this.openShareModal}
        />
        {this.renderShareModal()}
      </div>
    )
  }
}
