import React from 'react'
import { shallow, mount } from 'enzyme'
import EditableWorkflowName from './EditableWorkflowName'
import { okResponseMock, jsonResponseMock } from './utils'


describe('DataVersionSelect', () => {

  var wrapper; 

  describe('Read-only', () => {

    beforeEach(() => wrapper = shallow(
      <EditableWorkflowName
        value={'Test Title'}
        editClass=''
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

    // is API really needed here, or just mock functions?
    var api = {
      getWfModuleVersions: jsonResponseMock(),
      setWfModuleVersion: okResponseMock(),
    };
    var titleField;

    beforeEach(() => wrapper = mount(
      <EditableWorkflowName
        value={'Test Title'}
        editClass=''
        wfId={808}
        isReadOnly={false}
        api={api}
      />
    ));
    beforeEach(() => titleField = wrapper.find('RIETextArea'));    

  
    it('Renders a title that can be edited and saved', () => {
      expect(wrapper).toMatchSnapshot();

      // TODO: after all tests work, Refactor repeats into beforeEach

      expect(titleField.length).toBe(1);
      titleField.simulate('click');

      expect(wrapper).toMatchSnapshot();

      // now that area is clicked on, an editable field 
      let textArea = wrapper.find('.editable-title-field-active')
      expect(textArea.length).toBe(1);
      
      // enter some text

      // hit return

      // check state for title change

      // snapshot
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
