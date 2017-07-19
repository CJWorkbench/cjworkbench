import React from 'react'
import UpdateFrequencySelect  from './UpdateFrequencySelect'
import { mount } from 'enzyme'

it('UpdateFrequencySelect renders correctly', () => {

  const wrapper = mount(<UpdateFrequencySelect />);
  expect(wrapper).toMatchSnapshot();

  wrapper.setState( { modalOpen: true } )
  expect(wrapper).toMatchSnapshot();

});




