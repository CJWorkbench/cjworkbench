/* globals confirm */
// Elements of /workflows. Navbar plus a list

import React from 'react'
import Navbar from './Navbar'
import PropTypes from 'prop-types'
import ShareModal from '../ShareModal/Modal' // _not_ the Redux-connected component, 'ShareModal'
import { logUserEvent } from '../utils'
import CreateWorkflowButton from './CreateWorkflowButton'
import WorkflowLists from './WorkflowLists'
import { WorkflowListPropType } from './WorkflowList'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export class Workflows extends React.Component {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
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

  handleCloseShareModal = () => {
    this.setState({ shareModalWorkflowId: null })
  }

  logShare = (type) => {
    logUserEvent('Share workflow ' + type)
  }

  renderShareModal = () => {
    const { shareModalWorkflowId } = this.state

    if (shareModalWorkflowId === null) return null

    const workflow = this.allWorkflows.find(w => w.id === shareModalWorkflowId)
    if (!workflow) return null

    const url = `${window.origin}/workflows/${workflow.id}`

    return (
      <ShareModal
        url={url}
        acl={workflow.acl}
        ownerEmail={workflow.owner_email}
        workflowId={workflow.id}
        isReadOnly={!workflow.is_owner}
        isPublic={workflow.public}
        setIsPublic={this.setIsPublic}
        updateAclEntry={this.updateAclEntry}
        deleteAclEntry={this.deleteAclEntry}
        logShare={this.logShare}
        onClickClose={this.handleCloseShareModal}
      />
    )
  }

  // Ask the user if they really wanna do this. If sure, post DELETE to server
  deleteWorkflow = (workflowId) => {
    const tabName = this.workflowIdToTabName(workflowId)
    if (!tabName) return

    if (!confirm(this.props.i18n._(t('js.Workflows.delete.permanentyDeleteWarning')`Permanently delete this workflow?`))) return

    this.props.api.deleteWorkflow(workflowId)
      .then(() => {
        this.setState({
          workflows: {
            ...this.state.workflows,
            [tabName]: this.state.workflows[tabName].filter(w => w.id !== workflowId)
          }
        })
      })
  }

  duplicateWorkflow = (id) => {
    return this.props.api.duplicateWorkflow(id)
      .then(json => {
        // Add to beginning of owned list then set activeTab to owned
        this.setState({
          workflows: {
            ...this.state.workflows,
            owned: [json, ...this.state.workflows.owned]
          }
        })
      })
  }

  /**
   * Change properties of a Workflow in this.state.
   *
   * Calls setState().
   */
  _updateStateWorkflow = (workflowId, assignValues) => {
    const { workflows } = this.state
    // Find workflow category
    const category = Object.keys(workflows)
      .find(k => workflows[k].findIndex(w => w.id === workflowId) !== -1)
    // Copy its workflows, assigning `assignValues` to the one with ID `workflowId`
    const categoryWorkflows = workflows[category]
      .map(w => w.id === workflowId ? { ...w, ...assignValues } : w)

    const newWorkflows = {
      ...workflows,
      [category]: categoryWorkflows
    }
    this.setState({ workflows: newWorkflows })
  }

  setIsPublic = (isPublic) => {
    // Logic copied from ShareModal/actions
    const workflowId = this.state.shareModalWorkflowId
    this._updateStateWorkflow(workflowId, { public: isPublic })
    this.props.api.setWorkflowPublic(workflowId, isPublic) // ignoring whether it works
  }

  updateAclEntry = (email, canEdit) => {
    // Logic copied from ShareModal/actions
    const { workflows } = this.state
    const workflowId = this.state.shareModalWorkflowId
    // Find workflow
    const workflow = Object.keys(workflows)
      .flatMap(k => workflows[k])
      .find(w => w.id === workflowId)
    const acl = workflow.acl.slice() // shallow copy

    let index = acl.findIndex(entry => entry.email === email)
    if (index === -1) index = acl.length

    // overwrite or append the specified ACL entry
    acl[index] = { email, canEdit }

    acl.sort((a, b) => a.email.localeCompare(b.email))

    this._updateStateWorkflow(workflowId, { acl })
    this.props.api.updateAclEntry(workflowId, email, canEdit) // ignoring whether it works
  }

  deleteAclEntry = (email) => {
    // Logic copied from ShareModal/actions
    const { workflows } = this.state
    const workflowId = this.state.shareModalWorkflowId
    // Find workflow
    const workflow = Object.keys(workflows)
      .flatMap(k => workflows[k])
      .find(w => w.id === workflowId)
    const acl = workflow.acl.filter(entry => entry.email !== email)

    this._updateStateWorkflow(workflowId, { acl })
    this.props.api.deleteAclEntry(workflowId, email) // ignoring whether it works
  }

  render () {
    const { workflows } = this.state
    const { user, i18n } = this.props

    return (
      <div className='workflows-page'>
        <Navbar user={user} />
        <a href='/lessons/' className='lesson-banner mx-auto'>
          <div>
            <div className='content-1'>{i18n._(/* i18n: This should be all-caps for styling reasons */t('js.Workflows.new')`NEW`)}</div>
            <div className='d-flex'>
              <span className='icon-star' />
              <div className=' title-1 '>{i18n._(/* i18n: This should be all-caps for styling reasons */t('js.Workflows.training.title')`TRAINING`)}</div>
            </div>
          </div>
          <p>{i18n._(t('js.Workflows.learnHowToWorkWithData')`Learn how to work with data without coding`)}</p>
        </a>
        <CreateWorkflowButton>
          {i18n._(t('js.Workflows.createWorkflowButton')`Create Workflow`)}
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

export default withI18n()(Workflows)
