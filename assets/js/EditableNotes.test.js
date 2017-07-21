import React from 'react'
import { mount } from 'enzyme'
import EditableNotes from './EditableNotes'


it('EditableNotes renders correctly', () => {

  const wrapper = mount(<EditableNotes
    value={'testing'}
    editClass=""
    wf_module_id={1}
  />);
  expect(wrapper).toMatchSnapshot();

});