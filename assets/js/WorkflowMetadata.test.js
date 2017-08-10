import React from 'react'
import WorkflowMetadata  from './WorkflowMetadata'
import { shallow } from 'enzyme'
import { okResponseMock } from './utils'

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

  var api = {
    setWorkflowPublic: okResponseMock()
  };

  const wrapper = shallow(
    <WorkflowMetadata
      workflow={workflow}
      api={api}
    />);
  expect(wrapper).toMatchSnapshot();

  // Perfect, great. Now test that the dialog opens and setting to private calls the API
  var publicLink = wrapper.find('.test-button');
  expect(publicLink).toHaveLength(1);
  publicLink.first().simulate('click');

  setImmediate( () => {
    // Dialog should be open
    expect(wrapper).toMatchSnapshot();

    // Click the Private setting
    var privateButton = wrapper.find('.test-button-gray');
    expect(privateButton).toHaveLength(1);
    privateButton.first().simulate('click');
    setImmediate( () => {
      // Dialog should be closed, link should now say private
      expect(wrapper).toMatchSnapshot();
      // Check that the API was called
      expect(api.setWorkflowPublic.mock.calls.length).toBe(1);
      expect(api.setWorkflowPublic.mock.calls[0][0]).toBe(100);
      expect(api.setWorkflowPublic.mock.calls[0][1]).toBe(false);     // checking if False was passed in for isPublic argument
      
      expect(wrapper.state('isPublic')).toBe(false);  
      done();
    });
  });
});





