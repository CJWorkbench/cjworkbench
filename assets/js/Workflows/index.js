// Elements of /workflows. Navbar plus a list

import React from 'react'
import Navbar from './Navbar'
import PropTypes from 'prop-types'
import ShareModal from '../ShareModal/ModalLoader' // _not_ the Redux-connected component, 'ShareModal'
import { logUserEvent } from '../utils'
import CreateWorkflowButton from './CreateWorkflowButton'
import SortMenu from './SortMenu'
import WorkflowList from './WorkflowList'
import TabContent from 'reactstrap/lib/TabContent'
import TabPane from 'reactstrap/lib/TabPane'
import Nav from 'reactstrap/lib/Nav'
import NavItem from 'reactstrap/lib/NavItem'
import NavLink from 'reactstrap/lib/NavLink'

export default class Workflows extends React.Component {
  static propTypes = {
    api: PropTypes.object.isRequired,
    workflows: PropTypes.object.isRequired
  }

  state = {
    workflows: this.props.workflows,
    activeTab: this.props.workflows.owned.length === 0 ? 'templates' : 'owned',
    shareModalWorkflowId: null,
    comparator: 'last_update|descending'
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

  preventDefault = (ev) => {
    ev.preventDefault()
  }

  toggle (tab) {
    if (this.state.activeTab !== tab) {
      this.setState({
        activeTab: tab
      })
    }
  }

  setComparator = (comparator) => {
    this.setState({ comparator })
  }

  // sorting comparator
  propComparator = () => {
    // sort method determined by state array
    const prop = this.state.sortMethod.type
    const direction = this.state.sortMethod.direction
    switch (prop + '|' + direction) {
      case ('last_update|ascending'):
        return function (a, b) {
          return new Date(a['last_update']) - new Date(b['last_update'])
        }
      case ('name|ascending'):
        return function (a, b) {
          const first = a['name'].toLowerCase()
          const second = b['name'].toLowerCase()
          if (first < second) return -1
          if (first > second) return 1
          return 0
        }
      case ('name|descending'):
        return function (a, b) {
          const first = a['name'].toLowerCase()
          const second = b['name'].toLowerCase()
          if (second < first) return -1
          if (second > first) return 1
          return 0
        }
      // default sort modified descending
      default:
        return function (a, b) {
          return new Date(b['last_update']) - new Date(a['last_update'])
        }
    }
  }

  renderWorkflowPane = (workflows, tab) => {
    if (workflows.length > 0) {
      // Sort based on state, can only delete your own WFs
      return (
        <TabPane tabId={tab}>
          <WorkflowList
            workflows={workflows}
            comparator={this.state.comparator}
            duplicateWorkflow={this.duplicateWorkflow}
            deleteWorkflow={tab === 'owned' ? this.deleteWorkflow : null}
            openShareModal={this.openShareModal}
          />
        </TabPane>
      )
    } else if (tab === 'owned'){
      // Create workflow link if no owned workflows
      return (
        <TabPane tabId={'owned'}>
          <CreateWorkflowButton>
            Create your first workflow
          </CreateWorkflowButton>
        </TabPane>
      )
    } else if (tab === 'shared'){
      // No shared workflows message
      return (
        <TabPane tabId={'shared'}>
          <div className="placeholder">No shared workflows ~ ༼ つ ◕_◕ ༽つ</div>
        </TabPane>
      )
    } else if (tab === 'templates'){
      // No shared workflows message
      return (
        <TabPane tabId={'templates'}>
          <div className="placeholder">No template  \_(ツ)_/¯</div>
        </TabPane>
      )
    }
  }
  setTabOwned = () => this.setState({ activeTab: 'owned' })
  setTabShared = () => this.setState({ activeTab: 'shared' })
  setTabTemplates = () => this.setState({ activeTab: 'templates' })

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
        <div className='container'>
          <div className='mx-auto workflows-list'>
            <Nav tabs>
              <div className="tab-group">
                <NavItem active={activeTab === 'owned'} onClick={this.setTabOwned}>
                  <NavLink>
                    My workflows
                  </NavLink>
                </NavItem>
                <NavItem active={activeTab === 'shared'} onClick={this.setTabShared}>
                  <NavLink>
                    Shared with me
                  </NavLink>
                </NavItem>
                <NavItem active={activeTab === 'templates'} onClick={this.setTabTemplates}>
                  <NavLink>
                    Recipes
                  </NavLink>
                </NavItem>
              </div>
              <SortMenu comparator={comparator} setComparator={this.setComparator} />
            </Nav>
            <TabContent activeTab={this.state.activeTab}>
              { activeTab === 'owned' ? this.renderWorkflowPane(workflows.owned, 'owned') : null }
              { activeTab === 'shared' ? this.renderWorkflowPane(workflows.shared, 'shared') : null }
              { activeTab === 'templates' ? this.renderWorkflowPane(workflows.templates, 'templates') : null }
            </TabContent>
          </div>
        </div>
        {this.renderShareModal()}
      </div>
    )
  }
}
