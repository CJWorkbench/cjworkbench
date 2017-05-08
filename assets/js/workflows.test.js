import React from 'react';
import { mount } from 'enzyme';

import Workflows from './workflows';

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

  // Initial state, no workflows
  const wrapper = mount( <Workflows /> );
  expect(wrapper).toMatchSnapshot();

  // Now give it some actual workflows to work with
  wrapper.setState( {workflows: mockWorkflows, newWorkflowName: 'foop'} );
  expect(wrapper).toMatchSnapshot();
  expect(wrapper.find('.item-test-class')).toHaveLength(4);

  // Make sure there is a delete button for each workflow
  var buttons = wrapper.find('.button-test-class');
  expect(buttons).toHaveLength(4);

  // Try deleting a workflow
  global.confirm = () => true;                       // pretend the user clicked OK
  global.fetch = () => Promise.resolve({ok: true});  // respond to DELETE with Ok
  buttons.first().simulate('click');

  // We've clicked and now we have to wait for everything to update.
  // We do this with node's setImmediate and Jest's done https://facebook.github.io/jest/docs/asynchronous.html
  setImmediate( () => {
    expect(wrapper.find('.item-test-class')).toHaveLength(3);
    done();
  });

});

