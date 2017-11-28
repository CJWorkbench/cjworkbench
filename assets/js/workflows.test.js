import React from 'react'
import { mount } from 'enzyme'
import Workflows from './workflows'
const Utils = require('./utils');
import { mockResponse, okResponseMock, jsonResponseMock } from './utils'

describe('Workflow list page', () => {

  var testWorkflows = [
    {
      "id": 1,
      "name": "Charting",
      "public": true
    },
    {
      "id": 7,
      "name": "Messy data cleanup",
      "public": false
    },
    {
      "id": 8,
      "name": "Document search",
      "public": true
    },
    {
      "id": 9,
      "name": "Visualization",
      "public": false
    },
  ];

  var addResponse = {
    id: 543,
    name: 'New Workflow',
    public: false
  };

  var dupResponse = {
    id: 666,
    name: 'Copy of Visualization',
    public: false
  };

  var api;
  var wrapper;

  // Load the component and give it a list of workflows, before each test
  beforeEach( () => {
    api = {
      listWorkflows: jsonResponseMock(testWorkflows),
      newWorkflow: jsonResponseMock(addResponse),
      duplicateWorkflow: jsonResponseMock(dupResponse),
      deleteWorkflow: okResponseMock()
    };

    wrapper = mount(<Workflows api={api}/>);
  });

  it('renders correctly', (done) => {

    // postpone until promise resolves and our workflows load
    setImmediate( () => {
      expect(wrapper).toMatchSnapshot();

      expect(api.listWorkflows.mock.calls.length).toBe(1);

      // Make sure there is a context menu for each workflow
      var menus = wrapper.find('.menu-test-class');
      expect(menus).toHaveLength(4);

      // Make sure there is a metadata line for each workflow in the list
      menus = wrapper.find('.wf-id-meta');
      expect(menus).toHaveLength(4);

      done();
    })
  });

  it('delete a workflow', (done) => {

    global.confirm = () => true;                    // pretend the user clicked OK
    var workflowsReactObject = wrapper.get(0);
    workflowsReactObject.deleteWorkflow(9);         // invoke the callback passed to child menu component

    // We've clicked delete and now we have to wait for everything to update.
    // see https://facebook.github.io/jest/docs/asynchronous.html
    setImmediate(() => {
      expect(api.deleteWorkflow.mock.calls.length).toBe(1);
      expect(api.deleteWorkflow.mock.calls[0][0]).toBe(9);
      expect(wrapper.find('.item-test-class')).toHaveLength(3); // one fewer workflow
      done();
    });
  });


  it('new workflow button', (done) => {

    // mocking a global here... not really the greatest, ok for one test in this file
    Utils.goToUrl = jest.fn();

    // let 4 workflows load
    setImmediate( () => {
      expect(wrapper.find('.item-test-class')).toHaveLength(4);

      // Simulate click on New button - should create 'New Workflow' and go to page for new WF
      var newButton = wrapper.find('.new-workflow-button');
      newButton.first().simulate('click');

      setImmediate(() => {
        expect(api.newWorkflow.mock.calls.length).toBe(1);
        expect(api.newWorkflow.mock.calls[0][0]).toBe('New Workflow');
        expect(Utils.goToUrl.mock.calls.length).toBe(1);
        expect(Utils.goToUrl.mock.calls[0][0]).toBe('/workflows/543');
        done();
      });
    });
  });

  it('duplicate workflow callback', (done) => {

    // let 4 workflows load
    setImmediate( () => {
      expect(wrapper.find('.item-test-class')).toHaveLength(4);

      wrapper.instance().duplicateWorkflow(9);

      // should be a new item at the top of the list
      setImmediate(() => {
        expect(api.duplicateWorkflow.mock.calls.length).toBe(1);
        expect(api.duplicateWorkflow.mock.calls[0][0]).toBe(9);

        expect(wrapper.find('.item-test-class')).toHaveLength(5);

        done();
      });
    });
  });

});