import React, { useState } from 'react'
import PropTypes from 'prop-types'
import CreateWorkflowButton from './CreateWorkflowButton'
import SortMenu from './SortMenu'
import WorkflowList, { WorkflowListPropType } from './WorkflowList'

const Tab = React.memo(function Tab ({ name, isActive, setIsActive, children }) {
  return (
    <li className={`nav-item${isActive ? ' active' : ''}`}>
      <a
        id={`workflow-tab-link-${name}`}
        className={`nav-link${isActive ? ' active' : '' /* redundant */}`}
        aria-controls={`workflow-tab-${name}`}
        aria-selected={isActive}
        href={`#${name}`}
        onClick={setIsActive}
      >
        {children}
      </a>
    </li>
  )
})
Tab.propTypes = {
  name: PropTypes.oneOf([ 'owned', 'shared', 'templates' ]).isRequired,
  isActive: PropTypes.bool.isRequired,
  setIsActive: PropTypes.func.isRequired // func() => undefined
}

const TabPane = React.memo(function TabPane ({ name, isActive, children }) {
  return (
    <div
      className={`tab-pane${isActive ? ' show active' : ''}`}
      id={`workflow-tab-${name}`}
      role='tabpanel'
      aria-labelledby={`workflow-tab-link-${name}`}
    >
      {children}
    </div>
  )
})

const OwnedWorkflowList = React.memo(function OwnedWorkflowList ({ workflows, isActive, ...props }) {
  return (
    <TabPane name='owned' isActive={isActive}>
      {workflows.length > 0 ? (
        <WorkflowList workflows={workflows} {...props} />
      ) : (
        <CreateWorkflowButton>
          Create your first workflow
        </CreateWorkflowButton>
      )}
    </TabPane>
  )
})

const SharedWorkflowList = React.memo(function SharedWorkflowList ({ workflows, isActive, ...props }) {
  return (
    <TabPane name='shared' isActive={isActive}>
      {workflows.length > 0 ? (
        <WorkflowList workflows={workflows} {...props} deleteWorkflow={null} />
      ) : (
        <div className='placeholder'>No shared workflows ~ ༼ つ ◕_◕ ༽つ</div>
      )}
    </TabPane>
  )
})

const TemplatesWorkflowList = React.memo(function TemplatesWorkflowList ({ workflows, isActive, ...props }) {
  return (
    <TabPane name='templates' isActive={isActive}>
      {workflows.length > 0 ? (
        <WorkflowList workflows={workflows} {...props} deleteWorkflow={null} />
      ) : (
        <div className='placeholder'>No template  \_(ツ)_/¯</div>
      )}
    </TabPane>
  )
})

function WorkflowLists ({ workflows, deleteWorkflow, duplicateWorkflow, openShareModal }) {
  const [ activeTab, setActiveTab ] = useState(workflows.owned.length ? 'owned' : 'shared')
  const [ comparator, setComparator ] = useState('last_update|descending')
  const tabProps = (name) => ({
    name,
    isActive: activeTab === name,
    setIsActive: (ev) => { ev.preventDefault(); setActiveTab(name) }
  })
  const duplicateWorkflowAndSwitchTab = (workflowId) => {
  }
  const tabContentProps = (name) => ({
    isActive: activeTab === name,
    workflows: workflows[name],
    comparator,
    deleteWorkflow,
    duplicateWorkflow: (workflowId) => {
      // HACK for now: support fake promise -- https://github.com/facebook/react/issues/14769#issuecomment-462528230
      // This is what we want:
      //duplicateWorkflow(workflowId).then(() => setActiveTab('owned'))
      // ... but we're left with this for now. (It switches tabs before the
      // workflow is created, which looks glitchy.)
      setActiveTab('owned')
      duplicateWorkflow(workflowId)
    },
    openShareModal
  })

  return (
    <div className='workflow-lists'>
      <div className='nav'>
        <ul className='workflow-tabs' id='workflow-tabs' role='tablist'>
          <Tab {...tabProps('owned')}>My workflows</Tab>
          <Tab {...tabProps('shared')}>Shared with me</Tab>
          <Tab {...tabProps('templates')}>Recipes</Tab>
        </ul>
        <SortMenu comparator={comparator} setComparator={setComparator} />
      </div>
      <div className='tab-content'>
        <OwnedWorkflowList {...tabContentProps('owned')} />
        <SharedWorkflowList {...tabContentProps('shared')} />
        <TemplatesWorkflowList {...tabContentProps('templates')} />
      </div>
    </div>
  )
}
WorkflowLists.PropTypes = {
  workflows: PropTypes.shape({
    owned: WorkflowListPropType.isRequired,
    shared: WorkflowListPropType.isRequired,
    templates: WorkflowListPropType.isRequired
  }).isRequired,
  deleteWorkflow: PropTypes.func.isRequired, // func(id) => undefined
  duplicateWorkflow: PropTypes.func.isRequired, // func(id) => undefined
  openShareModal: PropTypes.func.isRequired // func(id) => undefined
}
export default React.memo(WorkflowLists)
