import React from 'react'
import { mount } from 'enzyme'
import { act } from 'react-dom/test-utils'
import Workflows from './index'
const Utils = require('../utils');
import { tick, okResponseMock, jsonResponseMock } from '../test-utils'

describe('Workflow list page', () => {
  const testWorkflows = {
    owned: [
      {
        id: 1,
        name: "Cleaning",
        owner_name: 'Fred Frederson',
        public: true,
        is_owner: true,
        last_update: '2010-10-18T00:30:00'
      },
      {
        id: 2,
        name: "Charting",
        owner_name: 'Fred Frederson',
        public: false,
        is_owner: true,
        last_update: '2010-10-18T00:20:00'
      },
      {
        id: 3,
        name: "Analysis",
        owner_name: 'Fred Frederson',
        public: false,
        is_owner: true,
        last_update: '2010-10-18T07:45:00'
      }
    ],
    shared: [
      {
        id: 7,
        name: "Messy data cleanup",
        owner_name: 'John Johnson',
        public: false,
        is_owner: false,
        last_update: '2010-10-18T00:30:00'
      },
      {
        id: 8,
        name: "Document search",
        owner_name: 'Sally Sallerson',
        public: true,
        is_owner: false,
        last_update: '2010-10-18T00:45:00'
      }
    ],
    templates: [
      {
        id: 10,
        name: "Demo 1",
        owner_name: 'Workbench',
        public: false,
        is_owner: false,
        last_update: '2010-10-18T00:30:00'
      }
    ]
  }

  const addResponse = {
    id: 543,
    name: 'Untitled Workflow',
    owner_name: 'Sally Sallerson',
    public: false,
  }

  const api = {
    duplicateWorkflow: jest.fn(),
    deleteWorkflow: okResponseMock()
  }
  const wrapper = (props) => mount(
    <Workflows
      api={api}
      user={{id: 1}}
      {...props}
    />
  )

  let globalConfirm
  beforeEach(() => {
    globalConfirm = global.confirm
    global.confirm = jest.fn()
  })
  afterEach(() => {
    global.confirm = globalConfirm
  })

  it('renders correctly', () => {
    const w = wrapper({ workflows: testWorkflows })
    expect(w).toMatchSnapshot()

    // owned tab should have 3 workflows
    w.find('.nav-link').findWhere(node => node.props().children === 'My workflows').simulate('click')
    expect(w.find('.tab-pane.active Workflow')).toHaveLength(3)
    // Make sure there is a context menu for each workflow
    expect(w.find('.tab-pane.active WorkflowContextMenu')).toHaveLength(3)
    // Make sure there is a metadata line for each workflow in the list
    expect(w.find('.tab-pane.active WorkflowMetadata')).toHaveLength(3)

    // shared tab should have 2 workflows
    w.find('.nav-link').findWhere(node => node.props().children === 'Shared with me').simulate('click')
    expect(w.find('.tab-pane.active Workflow')).toHaveLength(2)

    // template tab should have 1 workflow1
    w.find('.nav-link').findWhere(node => node.props().children === 'Recipes').simulate('click')
    expect(w.find('.tab-pane.active Workflow')).toHaveLength(1)
  })

  it('delete a workflow', (done) => {
    const w = wrapper({workflows: testWorkflows })
    global.confirm.mockReturnValue(true) // pretend the user clicked OK
    // We've clicked delete and now we have to wait for everything to update.
    // see https://facebook.github.io/jest/docs/asynchronous.html
    setImmediate(() => {
      // Shared tab should start with 2 workflows and have 1 after delete
      w.update()
      expect(w.find('.tab-pane.active Workflow')).toHaveLength(3)
      w.instance().deleteWorkflow(3)

      setImmediate(() => {
        w.update()
        expect(api.deleteWorkflow.mock.calls.length).toBe(1)
        expect(api.deleteWorkflow.mock.calls[0][0]).toBe(3)
        expect(w.find('.tab-pane.active Workflow')).toHaveLength(2) // one fewer workflow
        done()
      })
    })
  })

  it('duplicates a workflow', async () => {
    // let 2 workflows load in user's shared tab, duplicate 1 and activeTab should get set
    // to owned list with +1 worflow
    const w = wrapper({
      workflows: testWorkflows,
      api: {
        ...api,
        duplicateWorkflow: jest.fn(() => ({ // HACK for now: return fake promise -- https://github.com/facebook/react/issues/14769#issuecomment-462528230
          then: jest.fn(callback => act(() => callback({
            id: 666,
            name: 'Copy of Visualization',
            owner_name: 'Paul Plagarizer',
            public: false,
          })))
        }))
      }
    })

    // Owned list should start with 3 WFs, shared with 2
    expect(w.find('.tab-pane.active Workflow')).toHaveLength(3)
    w.find('.nav-link').findWhere(node => node.props().children === 'Shared with me').simulate('click')
    expect(w.find('.tab-pane.active Workflow')).toHaveLength(2)

    w.find('.tab-pane.active Workflow:first-child').prop('duplicateWorkflow')(7)
    expect(w.prop('api').duplicateWorkflow).toHaveBeenCalledWith(7)
    await tick()
    w.update()

    // Expect owned tab to now have 4 workflows
    // should be a new item at the top of the owned list
    expect(w.find('.tab-pane.active Workflow')).toHaveLength(4)
  })

  it('owned pane should have create workflow link when no workflows', () => {
    const workflows = { ...testWorkflows, owned: [] }
    const w = wrapper({ workflows })

    // Owned list should have no workflows, instead a create workflow link
    w.find('.nav-link').findWhere(node => node.props().children === 'My workflows').simulate('click')
    expect(w.find('.tab-pane.active Workflow')).toHaveLength(0)
    expect(w.find('.tab-pane.active CreateWorkflowButton')).toHaveLength(1)
  })

  it('shared and template panes should have a placeholder when no workflows', (done) => {
    const w = wrapper({ workflows: {
      owned: testWorkflows.owned,
      shared: [],
      templates: []
    }})
    setImmediate( () => {
      w.update()
      w.find('.nav-link').findWhere(node => node.props().children === 'Shared with me').simulate('click')
      expect(w.find('.tab-pane.active Workflow')).toHaveLength(0)
      expect(w.find('.tab-pane.active .placeholder')).toHaveLength(1)
      w.find('.nav-link').findWhere(node => node.props().children === 'Recipes').simulate('click')
      expect(w.find('.tab-pane.active Workflow')).toHaveLength(0)
      expect(w.find('.tab-pane.active .placeholder')).toHaveLength(1)
      done()
    })
  })

  it('should sort properly by date and name', () => {
    const w = wrapper({workflows: testWorkflows})

    // sort by date ascending
    w.find('.sort-menu DropdownToggle button').simulate('click')
    w.find('button[data-comparator="last_update|ascending"]').simulate('click')
    expect(w.find('.tab-pane.active Workflow').get(0).key).toEqual('2')
    expect(w.find('.tab-pane.active Workflow').get(1).key).toEqual('1')
    expect(w.find('.tab-pane.active Workflow').get(2).key).toEqual('3')

    // sort by date descending
    w.find('.sort-menu DropdownToggle button').simulate('click')
    w.find('button[data-comparator="last_update|descending"]').simulate('click')
    expect(w.find('.tab-pane.active Workflow').get(0).key).toEqual('3')
    expect(w.find('.tab-pane.active Workflow').get(1).key).toEqual('1')
    expect(w.find('.tab-pane.active Workflow').get(2).key).toEqual('2')

    // sort by name ascending
    w.find('.sort-menu DropdownToggle button').simulate('click')
    w.find('button[data-comparator="name|ascending"]').simulate('click')
    expect(w.find('.tab-pane.active Workflow').get(0).key).toEqual('3')
    expect(w.find('.tab-pane.active Workflow').get(1).key).toEqual('2')
    expect(w.find('.tab-pane.active Workflow').get(2).key).toEqual('1')

    // sort by name descending
    w.find('.sort-menu DropdownToggle button').simulate('click')
    w.find('button[data-comparator="name|descending"]').simulate('click')
    expect(w.find('.tab-pane.active Workflow').get(0).key).toEqual('1')
    expect(w.find('.tab-pane.active Workflow').get(1).key).toEqual('2')
    expect(w.find('.tab-pane.active Workflow').get(2).key).toEqual('3')
  })

  it('should allow delete of owned workflows', () => {
    const w = wrapper({ workflows: testWorkflows })
    w.find('.tab-pane.active .context-button').at(0).simulate('click')
    expect(w.find('.tab-pane.active button.delete-workflow')).toHaveLength(1)
  })

  it('should not allow delete of shared-with-me workflows', () => {
    const w = wrapper({ workflows: testWorkflows })
    w.find('.nav-link').findWhere(node => node.props().children === 'Shared with me').simulate('click')
    w.find('.tab-pane.active .context-button').at(0).simulate('click')
    expect(w.find('.tab-pane.active button.delete-workflow')).toHaveLength(0)
  })

  it('should not allow delete of templates', () => {
    const w = wrapper({ workflows: testWorkflows })
    w.find('.nav-link').findWhere(node => node.props().children === 'Recipes').simulate('click')
    w.find('.tab-pane.active .context-button').at(0).simulate('click')
    expect(w.find('.tab-pane.active button.delete-workflow')).toHaveLength(0)
  })
})
