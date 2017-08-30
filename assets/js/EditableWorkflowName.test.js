import React from 'react'
import { shallow, mount } from 'enzyme'
import EditableWorkflowName from './EditableWorkflowName'
import { okResponseMock } from './utils'


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

    it('Clicking on text does not change to edit state - dummy test', () => {
      // TODO: how to simulate click when there is no onCLick method on component?
      expect(true).toBe(true);
    });

  });

  describe('NOT Read-only', () => {

    var api = {
      setWfName: okResponseMock()
    };
    var titleField;

    beforeEach(() => wrapper = mount(
      <EditableWorkflowName
        value={'Test Title'}
        wfId={808}
        isReadOnly={false}
        api={api}
      />
    ));
    beforeEach(() => titleField = wrapper.find('.editable-title-field'));    

  
    it('Renders a title that can be edited and saved', () => {
      expect(wrapper).toMatchSnapshot();

      // TODO: finish test

    });

    it('Editing a title, then clicking Escape, will not save edits', () => {
      expect(true).toBe(true);

      // find element and click on it
      // 'Simulate' may not work, see what else can do

      // enter some text

      // hit Escape

      // check state for title no-change

      // snapshot

    });

    it('A deleted title is replaced with default text', () => {
      expect(true).toBe(true);

            // find element and click on it
      // 'Simulate' may not work, see what else can do

      // enter some text

      // hit Return

      // check state for default title

      // snapshot

    });


  });

});
