import React from 'react'
import { mount } from 'enzyme'
import Workflows from './workflows'
const Utils = require('./utils');
import { okResponseMock, jsonResponseMock } from './test-utils'

describe('Workflow list page', () => {
  const testWorkflows = {
    owned: [
      {
        id: 1,
        name: "Charting",
        owner_name: 'Fred Frederson',
        public: true,
        is_owner: true
      },
      {
        id: 2,
        name: "Analysis",
        owner_name: 'Fred Frederson',
        public: false,
        is_owner: true
      },
      {
        id: 3,
        name: "Cleaning",
        owner_name: 'Fred Frederson',
        public: false,
        is_owner: true
      }
    ],
    shared: [
      {
        id: 7,
        name: "Messy data cleanup",
        owner_name: 'John Johnson',
        public: false,
        is_owner: false
      },
      {
        id: 8,
        name: "Document search",
        owner_name: 'Sally Sallerson',
        public: true,
        is_owner: false
      }
    ],
    templates: [
      {
        id: 10,
        name: "Demo 1",
        owner_name: 'Workbench',
        public: false,
        is_owner: false
      }
    ]
  }

  const addResponse = {
    id: 543,
    name: 'New Workflow',
    owner_name: 'Sally Sallerson',
    public: false,
  }

  const dupResponse = {
    id: 666,
    name: 'Copy of Visualization',
    owner_name: 'Paul Plagarizer',
    public: false,
  }

  var api;
  var wrapper;

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

  // Load the component and give it a list of workflows, before each test
  beforeEach( () => {
    api = {
      newWorkflow: jsonResponseMock(addResponse),
      duplicateWorkflow: jsonResponseMock(dupResponse),
      deleteWorkflow: okResponseMock()
    }

    wrapper = mount(<Workflows api={api} workflows={testWorkflows}/>)
  })
  afterEach(() => wrapper.unmount())

  it('renders correctly', (done) => {

    // postpone until promise resolves and our workflows load
    setImmediate( () => {
      wrapper.update()
      expect(wrapper).toMatchSnapshot();

      // Make sure there is a context menu for each workflow
      var menus = wrapper.find('.menu-test-class');
      expect(menus).toHaveLength(6)

      // Make sure there is a metadata line for each workflow in the list
      menus = wrapper.find('.wf-meta--id');
      expect(menus).toHaveLength(6)

      done();
    })
  });

  it('delete a workflow', (done) => {
    global.confirm.mockReturnValue(true) // pretend the user clicked OK
    // We've clicked delete and now we have to wait for everything to update.
    // see https://facebook.github.io/jest/docs/asynchronous.html
    setImmediate(() => {
      // Shared tab should start with 2 workflows and have 1 after delete
      wrapper.update()
      expect(wrapper.find('.tab-pane.active').find('.workflow-item')).toHaveLength(3)
      wrapper.instance().deleteWorkflow(3)

      setImmediate(() => {
        wrapper.update()
        expect(api.deleteWorkflow.mock.calls.length).toBe(1)
        expect(api.deleteWorkflow.mock.calls[0][0]).toBe(3)
        expect(wrapper.find('.tab-pane.active').find('.workflow-item')).toHaveLength(2) // one fewer workflow
        done()
      })
    })
  })

  it('new workflow button', (done) => {
    // let 4 workflows load
    setImmediate( () => {
      var newButton = wrapper.find('.new-workflow-button');
      newButton.first().simulate('click');

      setImmediate(() => {
        expect(api.newWorkflow).toHaveBeenCalled()
        expect(Utils.goToUrl).toHaveBeenCalledWith('/workflows/543')
        done()
      })
    })
  })

  it('duplicate workflow callback', (done) => {
    // let 2 workflows load in user's shared tab, duplicate 1 and activeTab should get set
    // to owned list with +1 worflow
    setImmediate( () => {
      wrapper.update()

      // Owned list should start with 3 WFs, shared with 2
      expect(wrapper.find('.tab-pane.active').find('.workflow-item')).toHaveLength(3)
      let sharedTab = wrapper.find('.nav-link').findWhere(node => node.props().children === 'Shared with me')
      sharedTab.simulate('click')
      expect(wrapper.find('.tab-pane.active').find('.workflow-item')).toHaveLength(2)

      wrapper.instance().duplicateWorkflow(7)

      // should be a new item at the top of the owned list
      setImmediate(() => {
        wrapper.update()
        expect(api.duplicateWorkflow.mock.calls.length).toBe(1)
        expect(api.duplicateWorkflow.mock.calls[0][0]).toBe(7)

        // Expect owned tab to now have 4 workflows
        expect(wrapper.find('.tab-pane.active').find('.workflow-item')).toHaveLength(4)
        done()
      })
    })
  })
})
