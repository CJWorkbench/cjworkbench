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
    }).isRequired
  }

  state = {
    workflows: this.props.workflows, // we'll be editing this
    shareModalWorkflowId: null
  }

  get allWorkflows () {
    const workflows = this.state.workflows || {}
    return [].concat(...Object.keys(this.state.workflows || {}).map(k => workflows[k]))
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
  deleteWorkflow = (id) => {
    if (!confirm("Permanently delete this workflow?"))
      return

    this.props.api.deleteWorkflow(id)
    .then(response => {
      var workflowsMinusID = Object.assign({}, this.state.workflows)
      workflowsMinusID[this.state.activeTab] = workflowsMinusID[this.state.activeTab].filter(wf => wf.id !== id)
      this.setState({workflows: workflowsMinusID})
    })
  }

  duplicateWorkflow = (id) => {
    this.props.api.duplicateWorkflow(id)
      .then(json => {
        // Add to beginning of owned list then set activeTab to owned
        var workflowsPlusDup = Object.assign({}, this.state.workflows)
        workflowsPlusDup['owned'].unshift(json)
        this.setState({workflows: workflowsPlusDup, activeTab: 'owned'})
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

    return (
      <div className='workflows-page'>
        <Navbar />
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
