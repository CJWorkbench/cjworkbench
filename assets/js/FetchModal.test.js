import React from 'react';
import { shallow, render, mount } from 'enzyme';
import FetchModal from './FetchModal';

/*
it('renders correctly', () => {
  const tree = renderer.create(
    <FetchModal/>
  ).toJSON();
  expect(tree).toMatchSnapshot();
});

*/


it('renders correctly', () => {
  const wrapper = shallow( <FetchModal /> );
  expect(wrapper).toMatchSnapshot();
});

it('opens when button pressed', () => {
  const wrapper = mount( <FetchModal /> );
  expect(wrapper.state().modal).toBe(false);
  wrapper.find('button').simulate('click');
  expect(wrapper.state().modal).toBe(true);
});

