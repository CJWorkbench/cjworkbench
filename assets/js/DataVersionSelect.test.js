import React from 'react'
import DataVersionSelect  from './DataVersionSelect'
import { mount, shallow } from 'enzyme'
import { emptyAPI } from './utils'

it('DataVersionSelect renders correctly', () => {

  var mockVersions = {
    versions: [
      '1', '2', '3', '4', '5'
    ],
    selected: '4'
  };

  const wrapper = shallow( <DataVersionSelect wf_module_id={1} api={emptyAPI}/>);
  wrapper.setState( { modalOpen: false, versions: mockVersions, originalSelected:'4'} )
  expect(wrapper).toMatchSnapshot();

  // Test that dialog opens when clicked
  wrapper.find('.open-modal').simulate('click')
  expect(wrapper).toMatchSnapshot();
  expect(wrapper.find('.list-test-class')).toHaveLength(5);
});




