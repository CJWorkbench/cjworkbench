import React from 'react'
import { mount } from 'enzyme'
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

  const dupResponse = {
    id: 666,
    name: 'Copy of Visualization',
    owner_name: 'Paul Plagarizer',
    public: false,
  }

  const api = {
    newWorkflow: jsonResponseMock(addResponse),
    duplicateWorkflow: jsonResponseMock(dupResponse),
    deleteWorkflow: okResponseMock()
  }
  const wrapper = (props) => mount(<Workflows api={api} {...props} />)

  let globalGoToUrl
  beforeEach(() => {
    // mocking a global here... not really the greatest, ok for one test in this file
    globalGoToUrl = Utils.goToUrl
    Utils.goToUrl = jest.fn()
  })
  afterEach(() => {
    Utils.goToUrl = globalGoToUrl
  })

  let globalConfirm
  beforeEach(() => {
    globalConfirm = global.confirm
    global.confirm = jest.fn()
  })
  afterEach(() => {
    global.confirm = globalConfirm
  })

  // testWorkflows somehow gets modified during testing (even when const), must reset
  beforeEach(() => {
    testWorkflows.owned = testWorkflows.owned.filter(wf => wf.id !== 666)
  })

  it('renders correctly', () => {
    const w = wrapper({ workflows: testWorkflows })
    expect(w).toMatchSnapshot()

    // owned tab should have 3 workflows
    w.find('.nav-link').findWhere(node => node.props().children === 'My workflows').simulate('click')
    expect(w.find('Workflow')).toHaveLength(3)
    // Make sure there is a context menu for each workflow
    expect(w.find('WorkflowContextMenu')).toHaveLength(3)
    // Make sure there is a metadata line for each workflow in the list
    expect(w.find('WorkflowMetadata')).toHaveLength(3)

    // shared tab should have 2 workflows
    w.find('.nav-link').findWhere(node => node.props().children === 'Shared with me').simulate('click')
    expect(w.find('Workflow')).toHaveLength(2)

    // template tab should have 1 workflow1
    w.find('.nav-link').findWhere(node => node.props().children === 'Recipes').simulate('click')
    expect(w.find('Workflow')).toHaveLength(1)
  })

  it('delete a workflow', (done) => {
    const w = wrapper({workflows: testWorkflows })
    global.confirm.mockReturnValue(true) // pretend the user clicked OK
    // We've clicked delete and now we have to wait for everything to update.
    // see https://facebook.github.io/jest/docs/asynchronous.html
    setImmediate(() => {
      // Shared tab should start with 2 workflows and have 1 after delete
      w.update()
      expect(w.find('Workflow')).toHaveLength(3)
      w.instance().deleteWorkflow(3)

      setImmediate(() => {
        w.update()
        expect(api.deleteWorkflow.mock.calls.length).toBe(1)
        expect(api.deleteWorkflow.mock.calls[0][0]).toBe(3)
        expect(w.find('Workflow')).toHaveLength(2) // one fewer workflow
        done()
      })
    })
  })

  it('new workflow button', (done) => {
    const w = wrapper({workflows: testWorkflows })
    // let 4 workflows load
    setImmediate( () => {
      var newButton = w.find('.new-workflow-button');
      newButton.first().simulate('click');

      setImmediate(() => {
        expect(api.newWorkflow).toHaveBeenCalled()
        expect(Utils.goToUrl).toHaveBeenCalledWith('/workflows/543')
        done()
      })
    })
  })

  it('duplicates a workflow', async () => {
    // let 2 workflows load in user's shared tab, duplicate 1 and activeTab should get set
    // to owned list with +1 worflow
    const w = wrapper({ workflows: testWorkflows })
    await tick()

    // Owned list should start with 3 WFs, shared with 2
    expect(w.find('Workflow')).toHaveLength(3)
    let sharedTab = w.find('.nav-link').findWhere(node => node.props().children === 'Shared with me')
    sharedTab.simulate('click')
    expect(w.find('Workflow')).toHaveLength(2)

    w.instance().duplicateWorkflow(7)

    // should be a new item at the top of the owned list
    await tick()
    w.update()
    expect(api.duplicateWorkflow.mock.calls.length).toBe(1)
    expect(api.duplicateWorkflow.mock.calls[0][0]).toBe(7)

    // Expect owned tab to now have 4 workflows
    expect(w.find('Workflow')).toHaveLength(4)
  })

  it('owned pane should have create workflow link when no workflows', (done) => {
    let modifiedWorkflows = Object.assign({}, testWorkflows)
    modifiedWorkflows['owned'] = {}
    const w = wrapper({workflows: modifiedWorkflows})
    setImmediate( () => {
      w.update()
      // Owned list should have no workflows, instead a create workflow link
      expect(w.find('Workflow')).toHaveLength(0)
      expect(w.find('.tab-pane.active .new-workflow-link')).toHaveLength(1)
      done()
    })
  })

  it('shared and template panes should have a placeholder when no workflows', (done) => {
    let modifiedWorkflows = Object.assign({}, testWorkflows)
    modifiedWorkflows['shared'] = {}
    modifiedWorkflows['templates'] = {}
    const w = wrapper({workflows: modifiedWorkflows})
    setImmediate( () => {
      w.update()
      w.find('.nav-link').findWhere(node => node.props().children === 'Shared with me').simulate('click')
      expect(w.find('Workflow')).toHaveLength(0)
      expect(w.find('.tab-pane.active .placeholder')).toHaveLength(1)
      w.find('.nav-link').findWhere(node => node.props().children === 'Recipes').simulate('click')
      expect(w.find('Workflow')).toHaveLength(0)
      expect(w.find('.tab-pane.active .placeholder')).toHaveLength(1)
      done()
    })
  })

  it('should sort properly by date and name', (done) => {
    const w = wrapper({workflows: testWorkflows})
    setImmediate( () => {
      // sort by date ascending
      w.update()
      w.find('button[data-comparator="last_update|ascending"]').simulate('click')
      expect(w.find('Workflow').get(0).key).toEqual('2')
      expect(w.find('Workflow').get(1).key).toEqual('1')
      expect(w.find('Workflow').get(2).key).toEqual('3')
      // sort by date descending
      w.update()
      w.find('button[data-comparator="last_update|descending"]').simulate('click')
      expect(w.find('Workflow').get(0).key).toEqual('3')
      expect(w.find('Workflow').get(1).key).toEqual('1')
      expect(w.find('Workflow').get(2).key).toEqual('2')
      // sort by name ascending
      w.update()
      w.find('button[data-comparator="name|ascending"]').simulate('click')
      expect(w.find('Workflow').get(0).key).toEqual('3')
      expect(w.find('Workflow').get(1).key).toEqual('2')
      expect(w.find('Workflow').get(2).key).toEqual('1')
      // sort by name descending
      w.update()
      w.find('button[data-comparator="name|descending"]').simulate('click')
      expect(w.find('Workflow').get(0).key).toEqual('1')
      expect(w.find('Workflow').get(1).key).toEqual('2')
      expect(w.find('Workflow').get(2).key).toEqual('3')
      done()
    })
  })

  it('should only render the delete option for owned workflows', (done) => {
    const w = wrapper({workflows: testWorkflows})
    setImmediate( () => {
      // my workflows tab
      w.update()
      expect(w.find('.tab-pane.active button.delete-workflow')).toHaveLength(3)
      // shared workflows tab
      w.find('.nav-link').findWhere(node => node.props().children === 'Shared with me').simulate('click')
      expect(w.find('.tab-pane.active .delete-workflow')).toHaveLength(0)
      // templates tab
      w.find('.nav-link').findWhere(node => node.props().children === 'Recipes').simulate('click')
      expect(w.find('.tab-pane.active .delete-workflow')).toHaveLength(0)
      done()
    })
  })

})
