import React from 'react'
import UpdateFrequencySelect  from './UpdateFrequencySelect'
import { mount } from 'enzyme'

it('UpdateFrequencySelect renders correctly', () => {

  const wrapper = mount(<UpdateFrequencySelect
    updateSettings= {{
      lastUpdateCheck: 2,
      autoUpdateData: true,
      updateInterval: 5,
      updateUnits: 'minutes'
    }}
    wfModuleId={1}
   />);
  expect(wrapper).toMatchSnapshot();

  wrapper.setState( { modalOpen: true } )
  expect(wrapper).toMatchSnapshot();

});




