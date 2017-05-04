import React from 'react';
import { shallow, render, mount } from 'enzyme';

import ModuleMenu from './ModuleMenu';

it('renders correctly', () => {

  var mockModules = [
    {
      "id": 9,
      "name": "Cast",
      "category": "Wrangle"
    },
    {
      "id": 6,
      "name": "Chart",
      "category": "Visualize"
    },
    {
      "id": 1,
      "name": "Formula",
      "category": "Analyze"
    },
    {
      "id": 2,
      "name": "Load From URL",
      "category": "Sources"
    },
    {
      "id": 10,
      "name": "Melt",
      "category": "Wrangle"
    }
    ];


  const wrapper = shallow( <ModuleMenu addModule={ () => {} } /> );
  expect(wrapper).toMatchSnapshot();

  // Now give it some actual menu items
  wrapper.setState( {dropdownOpen: true, items: mockModules} )
  expect(wrapper).toMatchSnapshot();
});

