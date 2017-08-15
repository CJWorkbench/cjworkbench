import React from 'react'
import WfContextMenu  from './WfContextMenu'
import { shallow } from 'enzyme'
import { okResponseMock } from './utils'


it('WfContextMenu renders correctly', () => {

  var api = {
    deleteWorkflow: okResponseMock(),
    shareWorkflow: okResponseMock()
  };

  const wrapper = shallow(
    <WfContextMenu 
      deleteWorkflow={api.deleteWorkflow} 
      shareWorkflow={api.shareWorkflow}
    />
  );

  expect(wrapper).toMatchSnapshot();

  // find and click Delete option
  let deleteLink = wrapper.find('.test-delete-button');
  expect(deleteLink).toHaveLength(1);
  deleteLink.simulate('click');

  expect(wrapper).toMatchSnapshot();
  
  // find and click Share option
  // (not a currently functional button)
  let shareLink = wrapper.find('.test-share-button');
  expect(shareLink).toHaveLength(1);
  shareLink.simulate('click');

  expect(wrapper).toMatchSnapshot();
  
  // check on API calls
  expect(api.deleteWorkflow.mock.calls.length).toBe(1);
  expect(api.shareWorkflow.mock.calls.length).toBe(1);

});





