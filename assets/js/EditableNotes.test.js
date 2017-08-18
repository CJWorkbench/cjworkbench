import React from 'react'
import { shallow, mount } from 'enzyme'
import EditableNotes from './EditableNotes'
import { okResponseMock } from './utils'


describe('EditableNotes', () => {

  var wrapper; 
  var api = {
    setWfModuleNotes: okResponseMock()
  };

  // 'Read-only, starts focused' is not necessary, as Focus and ReadOnly do not happen together

  describe('Read-only, starts NOT focused', () => {

    beforeEach(() => wrapper = shallow(
      <EditableNotes
        value={'This is the best module'}
        editClass=''
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

    it('Clicking on text does not change to edit state - dummy test', () => {
      expect(true).toBe(true);
    });

  });

  describe('NOT Read-only, starts focused', () => {

    beforeEach(() => wrapper = mount(
      <EditableNotes
        value={'This is the best module'}
        editClass=''
        wfModuleId={808}
        api={{}}
        isReadOnly={false}
        hideNotes={ () => {} }
        startFocused={true}
      />
    ));
  
    it('Renders note in edit state at start', () => {
      expect(wrapper).toMatchSnapshot();
    });

    it('A new note may be entered and saved - dummy test', () => {
      expect(true).toBe(true);
    });

    it('If a new note is blank, will save default text and close - dummy test', () => {
      expect(true).toBe(true);
    });

    it('A new note may be entered, but Escape key will cancel input - dummy test', () => {
      expect(true).toBe(true);
    });

  });

  describe('NOT Read-only, starts not focused', () => {

    beforeEach(() => wrapper = mount(
      <EditableNotes
        value={'This is the best module'}
        editClass=''
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

    it('Note may be clicked on to bring up edit state - dummy test', () => {
      expect(true).toBe(true);
    });

  });

});
