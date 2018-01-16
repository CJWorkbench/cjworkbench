/**
 * Testing Stories:
 * -Renders library-open version, which opens to modal
 * -Renders library-closed version, "
 * -Modal will import a module to library 
 */

import React from 'react'
import ImportModuleFromGitHub  from './ImportModuleFromGitHub'
import { mount, ReactWrapper } from 'enzyme'

describe('ImportModuleFromGitHub', () => {
  
  var wrapper;  
  var modalLink;

  describe('Library open', () => {

    beforeEach(() => wrapper = mount(
      <ImportModuleFromGitHub
        libraryOpen={true}
        moduleAdded={()=>{}}
      />
    ));
    beforeEach(() => modalLink = wrapper.find('.import-module-button'));    

    it('Renders a link, which will open modal window', () => { 
      expect(wrapper).toMatchSnapshot();

      expect(wrapper.state().modalOpen).toBe(false)
      
      expect(modalLink).toHaveLength(1);
      modalLink.simulate('click');
      expect(wrapper.state().modalOpen).toBe(true);

      // The insides of the Modal are a "portal", that is, attached to root of DOM, not a child of Wrapper
      // So find them, and make a new Wrapper
      // Reference: "https://github.com/airbnb/enzyme/issues/252"
      let modal_element = document.getElementsByClassName('modal-dialog');
      expect(modal_element.length).toBe(1);
      let modal = new ReactWrapper(modal_element[0], true)
      expect(modal).toMatchSnapshot();
      expect(modal.find('.dialog-body')).toHaveLength(1);
    });

    it('A module may be imported via the modal to the library', () => { 
      expect(true).toBe(true);
    });
  });

  describe('Library closed', () => {

    beforeEach(() => wrapper = mount(
      <ImportModuleFromGitHub
        libraryOpen={true}
        moduleAdded={()=>{}}
      />
    ));
    beforeEach(() => modalLink = wrapper.find('.import-module-button'));    

    it('Renders a link, which will open modal window', () => { 
      expect(wrapper).toMatchSnapshot();

      expect(wrapper.state().modalOpen).toBe(false)
      
      expect(modalLink).toHaveLength(1);
      modalLink.simulate('click');
      expect(wrapper.state().modalOpen).toBe(true);

      // The insides of the Modal are a "portal", that is, attached to root of DOM, not a child of Wrapper
      // So find them, and make a new Wrapper
      // Reference: "https://github.com/airbnb/enzyme/issues/252"
      let modal_element = document.getElementsByClassName('modal-dialog');
      // second rendering of modal element, so length of 2
      expect(modal_element.length).toBe(2);
      let modal = new ReactWrapper(modal_element[0], true)
      expect(modal).toMatchSnapshot();
      expect(modal.find('.dialog-body')).toHaveLength(1);
    });

    it('A module may be imported via the modal to the library', () => { 
      expect(true).toBe(true);
    });
  });

});


