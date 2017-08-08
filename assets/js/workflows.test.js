import React from 'react'
import { mount } from 'enzyme'
import Workflows from './workflows'
const Utils = require('./utils');

it('renders correctly', (done) => {

  var mockWorkflows = [
      {
        "id": 1,
        "name": "Charting"
      },
      {
        "id": 7,
        "name": "Messy data cleanup"
      },
      {
        "id": 8,
        "name": "Document search"
      },
      {
        "id": 9,
        "name": "Visualization"
      },
    ];

  window.fetch = jest.fn().mockImplementation(()=>
    Promise.resolve(Utils.mockResponse(200, null, null))
  );

  // Start with no workflows on the initial fetch (won't get loaded before expects anyway, due to asynchrony)
  const wrapper = mount( <Workflows /> );
  expect(wrapper).toMatchSnapshot();
  
  // Manually add workflows by setting state
  wrapper.setState( { workflows: mockWorkflows} )
  expect(wrapper).toMatchSnapshot();
  expect(wrapper.find('.item-test-class')).toHaveLength(4);

  // Make sure there is a context menu for each workflow
  var menus = wrapper.find('.menu-test-class');
  expect(menus).toHaveLength(4);


  // Try deleting a workflow
  var workflowsReactObject = wrapper.get(0)
  global.confirm = () => true;                       // pretend the user clicked OK
  workflowsReactObject.deleteWorkflow(9)


  // We've clicked and now we have to wait for everything to update.
  // We do this with node's setImmediate and Jest's done https://facebook.github.io/jest/docs/asynchronous.html
  setImmediate( () => {
    expect(wrapper.find('.item-test-class')).toHaveLength(3);
    done();
  });

});

it('new workflow button', (done) => {

  const wrapper = mount( <Workflows /> );  

  // Simulate click on New button - should go to page for new WF
  var newButton = wrapper.find('.new-workflow-button');
  var testData =
    {
      id: 543,
      name: "New Workflow"
    };

  // Over-write default behavior (changing page)
  Utils.goToUrl = jest.fn();
  window.fetch = jest.fn().mockImplementation(()=>
    Promise.resolve(Utils.mockResponse(200, null, JSON.stringify(testData)))
  );
  newButton.first().simulate('click');

  setImmediate( () => {
    expect(Utils.goToUrl.mock.calls.length).toBe(1);
    expect(Utils.goToUrl.mock.calls[0][0]).toBe('/workflows/543');
    done();
  });

});

