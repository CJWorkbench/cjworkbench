import React from 'react'
import { mount } from 'enzyme'
import EditableWorkflowName from './EditableWorkflowName'


it('EditableWorkflowName renders correctly', () => {

  const wrapper = mount(<EditableWorkflowName
    value={'Test Title'}
    editClass=""
    wfId={1}
  />);
  expect(wrapper).toMatchSnapshot();

});