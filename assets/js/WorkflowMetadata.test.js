import React from 'react'
import WorkflowMetadata  from './WorkflowMetadata'
import { shallow } from 'enzyme'

const Utils = require('./utils');

var today = new Date();
var day_before = today.setDate(today.getDate() - 2);

it('WorkflowMetadata renders correctly', (done) => {

  var workflow = {
    id: 100,
    public: true,
    owner_name: "Harry Harrison",
    last_update: day_before
  };

  var apiCall = jest.fn().mockImplementation(()=>
    Promise.resolve(Utils.mockResponse(200, null, null))
  );
  var api = {
    setWorkflowPublic: apiCall
  };

  const wrapper = shallow(
    <WorkflowMetadata
      workflow={workflow}
      api={api}
    />);
  expect(wrapper).toMatchSnapshot();

  // Perfect, great. Now test that the dialog opens and setting to private calls the API
  var publicLink = wrapper.find('.t-f-blue');
  expect(publicLink).toHaveLength(1);
  publicLink.first().simulate('click');

  setImmediate( () => {
    // Dialog should be open
    expect(wrapper).toMatchSnapshot();

    // Click the private link
    var privateButton = wrapper.find('.button-gray');
    expect(privateButton).toHaveLength(1);
    privateButton.first().simulate('click');
    setImmediate( () => {
      // Dialog should be closed, link should now say private
      expect(wrapper).toMatchSnapshot();
      done();
    });
  });
});





