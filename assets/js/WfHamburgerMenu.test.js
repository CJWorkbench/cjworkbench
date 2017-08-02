import React from 'react'
import WfHamburgerMenu  from './WfHamburgerMenu'
import { mount } from 'enzyme'


it('renders correctly', () => {
  const wrapper = mount(
    <WfHamburgerMenu workflowId={1}/>
  );
  expect(wrapper).toMatchSnapshot();
});

it('renders correctly for workflows list page', () => {
  const wrapper = mount(
    <WfHamburgerMenu />
  );
  expect(wrapper).toMatchSnapshot();
});



