import React from 'react'
import { shallow, render, mount } from 'enzyme'

import MenuParam from './MenuParam';

it('renders correctly', () => {
  var menuStr = 'Apple|Kittens|Banana';

  const wrapper = shallow( <MenuParam items={menuStr} name="SuperMenu" selectedIdx={1} onChange={ () => {} } /> );
  expect(wrapper).toMatchSnapshot();
});

