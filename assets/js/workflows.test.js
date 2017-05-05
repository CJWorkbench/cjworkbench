import React from 'react';
import { shallow } from 'enzyme';

import Workflows from './workflows';

it('renders correctly', () => {

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

  const wrapper = shallow( <Workflows /> );
  expect(wrapper).toMatchSnapshot();

  // Now give it some actual workflows to work with
  wrapper.setState( {workflows: mockWorkflows, newWorkflowName: 'foop'} )
  expect(wrapper).toMatchSnapshot();
});

