import React from 'react'
import { shallow, mount } from 'enzyme'
import EditableNotes from './EditableNotes'
import { okResponseMock } from './utils'


describe('EditableNotes', () => {

  var wrapper; 
  var api = {
    setWfModuleNotes: okResponseMock()
  };
  var notesField;

  // 'Read-only, starts focused' is not necessary, as Focus and ReadOnly do not happen together

  describe('Read-only, starts NOT focused', () => {

    beforeEach(() => wrapper = shallow(
      <EditableNotes
        value={'This is the best module'}
        wfModuleId={808}
        api={{}}
        isReadOnly={true}
        hideNotes={ () => {} }
        startFocused={false}
      />
    ));
  
    it('Renders plain note', () => {
      expect(wrapper).toMatchSnapshot();
    });

  });

  describe('NOT Read-only, starts focused', () => {

    beforeEach(() => wrapper = mount(
      <EditableNotes
        value={'This is the best module'}
        wfModuleId={808}
        api={api}
        isReadOnly={false}
        hideNotes={ () => {} }
        startFocused={true}
      />
    ));
    beforeEach(() => notesField = wrapper.find('.editable-notes-field'));        
  
    it('Renders note in edit state at start', () => {
      expect(wrapper).toMatchSnapshot();
    });

    it('A new note may be entered and saved', () => {
      expect(notesField).toHaveLength(1);
      expect(wrapper.state().value).toEqual('This is the best module');
      notesField.simulate('change', {target: {value: 'This is a mediocre module'}});
      // Blur to trigger save
      notesField.simulate('blur');
      // Check that the API was called
      expect(api.setWfModuleNotes.mock.calls.length).toBe(1);
      // Check that default note is saved instead    
      expect(api.setWfModuleNotes.mock.calls[0][1]).toBe('This is a mediocre module'); 
     
      expect(wrapper.state().value).toEqual('This is a mediocre module');

    });

    it('If a new note is blank, will save default text and close', () => {

      expect(wrapper.state().value).toEqual('This is the best module');
      notesField.simulate('change', {target: {value: ''}});
      // Blur to trigger save
      notesField.simulate('blur');
      // Check that the API was called again
      expect(api.setWfModuleNotes.mock.calls.length).toBe(2);
      // Check that default note is saved instead     
      expect(api.setWfModuleNotes.mock.calls[1][1]).toBe("Write notes here"); 
    });

  });

  describe('NOT Read-only, starts not focused', () => {

    beforeEach(() => wrapper = mount(
      <EditableNotes
        value={'This is the best module'}
        wfModuleId={808}
        api={{}}
        isReadOnly={false}
        hideNotes={ () => {} }
        startFocused={false}
      />
    ));
  
    it('Renders note in non-edit state at start', () => {
      expect(wrapper).toMatchSnapshot();
    });

  });

});
