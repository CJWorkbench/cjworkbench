import React from 'react'
import { shallow, mount } from 'enzyme'
import EditableWorkflowName from './EditableWorkflowName'
import { okResponseMock } from './test-utils'


describe('EditableWorkflowName', () => {

  var wrapper;

  describe('Read-only', () => {

    beforeEach(() => wrapper = shallow(
      <EditableWorkflowName
        value={'Test Title'}
        wfId={808}
        isReadOnly={true}
        api={{}}
      />
    ));

    it('Renders plain title', () => {
      expect(wrapper).toMatchSnapshot();
    });

  });

  describe('NOT Read-only', () => {

    var api = {
      setWfName: okResponseMock()
    };
    var container;
    var titleField;

    beforeEach(() => wrapper = mount(
      <EditableWorkflowName
        value={'Test Title'}
        wfId={808}
        isReadOnly={false}
        api={api}
      />
    ));
    beforeEach(() => container = wrapper.find('.editable-title--container'));    
    beforeEach(() => titleField = wrapper.find('.editable-title--field'));
    afterEach(() => wrapper.unmount())


    it('Renders a title that can be edited and saved', () => {
      expect(wrapper).toMatchSnapshot();

      // confirm existence of targets
      expect(container).toHaveLength(1);
      expect(titleField).toHaveLength(1);

      // check value of field
      expect(wrapper.state().value).toEqual('Test Title');

      // click on container to select text
      container.first().simulate('click');

      // change the field value
      titleField.simulate('change', {target: {value: 'New Title'}});

      // Value of field should have changed
      expect(wrapper.state().value).toEqual('New Title');
    });

  });

});
