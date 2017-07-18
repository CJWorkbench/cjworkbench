import React from 'react'
import DataVersionSelect  from './DataVersionSelect'
import { mount, shallow } from 'enzyme'
import { emptyAPI } from './utils'

it('DataVersionSelect renders correctly', () => {

  // Force time zone to make sure tests always give same result
  process.env.TZ = 'UTC';

  var mockVersions = {
    versions: [
<<<<<<< HEAD
      '2017-07-10T17:57:58.324', 
      '2017-06-10T17:57:58.324', 
      '2017-05-10T17:57:58.324', 
      '2017-04-10T17:57:58.324', 
      '2017-03-10T17:57:58.324'
    ],
    selected: '2017-04-10T17:57:58.324'
  };

  const wrapper = shallow( <DataVersionSelect wf_module_id={1} api={emptyAPI}/>);
=======
      '2017-07-10 17:57:58.324', 
      '2017-06-10 17:57:58.324', 
      '2017-05-10 17:57:58.324', 
      '2017-04-10 17:57:58.324', 
      '2017-03-10 17:57:58.324'
    ],
    selected: '2017-04-10 17:57:58.324'
  };

  
  var localToUTC = (new Date()).getTimezoneOffset();  // how many hours off from UTC are we? print tests all in UTC

  const wrapper = shallow( <DataVersionSelect wf_module_id={1} api={emptyAPI} timezone_offset={localToUTC} />);
>>>>>>> master
  wrapper.setState( { modalOpen: false, versions: mockVersions, originalSelected:'4'} )
  expect(wrapper).toMatchSnapshot();

  // Test that dialog opens when clicked
  wrapper.find('.open-modal').simulate('click')
  expect(wrapper).toMatchSnapshot();
  expect(wrapper.find('.list-test-class')).toHaveLength(5);
});




