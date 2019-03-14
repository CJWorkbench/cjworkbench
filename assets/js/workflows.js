// Elements of /workflows. Navbar plus a list

import React from 'react'
import WorkflowListNavBar from './WorkflowListNavBar'
import WfContextMenu from './WfContextMenu'
import WorkflowMetadata from './WorkflowMetadata'
import PropTypes from 'prop-types'
import ShareModal from './ShareModal/ModalLoader' // _not_ the Redux-connected component, 'ShareModal'
import { goToUrl, logUserEvent } from './utils'
import WfSortMenu from './WfSortMenu'
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
    sortMethod: {type: 'last_update', direction: 'descending'}
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

  // Make a new workflow when button clicked, and navigate to its Module List page
  click = (e) => {
    this.props.api.newWorkflow()
      .then(json => {
        // navigate to new WF page
        goToUrl('/workflows/' + json.id)
      })
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

  setSortType = (sortType) => {
    this.setState({sortMethod: sortType})
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
          <div className='workflows-item--wrap'>
            {workflows.slice().sort(this.propComparator()).map(workflow => (
              <a href={'/workflows/' + workflow.id} className='workflow-item' key={workflow.id}>
                <div className='mt-1'>
                  <div className='workflow-title'>{workflow.name}</div>
                  <div className='wf-meta--id'>
                    <WorkflowMetadata
                      workflow={workflow}
                      openShareModal={this.openShareModal}
                    />
                  </div>
                </div>
                <div onClick={this.preventDefault} className='menu-test-class'>
                  <WfContextMenu
                    duplicateWorkflow={() => this.duplicateWorkflow(workflow.id)}
                    deleteWorkflow={() => this.deleteWorkflow(workflow.id)}
                    canDelete={tab === 'owned'}
                  />
                </div>
              </a>
            ))}
          </div>
        </TabPane>
      )
    } else if (tab === 'owned'){
      // Create workflow link if no owned workflows
      return (
        <TabPane tabId={'owned'}>
          <div>
            <a className={'new-workflow-link'} onClick={this.click}>Create your first workflow</a>
          </div>
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
    return (
      <div className='workflows-page'>
        <WorkflowListNavBar />
        <div className='container'>
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
          <div className='d-flex justify-content-center'>
            <button className='button-blue action-button new-workflow-button' onClick={this.click}>Create Workflow</button>
          </div>
          <div className='mx-auto workflows-list'>
            <Nav tabs>
              <div className="tab-group">
                <NavItem active={this.state.activeTab === 'owned'} onClick={this.setTabOwned}>
                  <NavLink>
                    My workflows
                  </NavLink>
                </NavItem>
                <NavItem active={this.state.activeTab === 'shared'} onClick={this.setTabShared}>
                  <NavLink>
                    Shared with me
                  </NavLink>
                </NavItem>
                <NavItem active={this.state.activeTab === 'templates'} onClick={this.setTabTemplates}>
                  <NavLink>
                    Recipes
                  </NavLink>
                </NavItem>
              </div>
              <div className="sort-group">
                <span>Sort</span>
                <WfSortMenu setSortType={this.setSortType} sortDirection={this.state.sortMethod.direction} />
              </div>
            </Nav>
            <TabContent activeTab={this.state.activeTab}>
              { this.renderWorkflowPane(this.state.workflows.owned, 'owned') }
              { this.renderWorkflowPane(this.state.workflows.shared, 'shared') }
              { this.renderWorkflowPane(this.state.workflows.templates, 'templates') }
            </TabContent>
          </div>
        </div>
        {this.renderShareModal()}
      </div>
    )
  }
}
