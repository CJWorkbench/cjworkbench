/**
 * Testing Stories:
 * -Renders library-open version, which opens to modal
 * -Renders library-closed version, "
 * -Modal will call API to begin import process
 * 
 */

import React from 'react'
import ImportModuleFromGitHub  from './ImportModuleFromGitHub'
import { mount, ReactWrapper } from 'enzyme'
import { jsonResponseMock } from './utils'

describe('ImportModuleFromGitHub', () => {
  
  var wrapper;  
  var modalLink;
  var moduleAdded = jest.fn();
  var api = {
    importFromGithub: jsonResponseMock()  // what should this return?
  };

  describe('Library open', () => {

    beforeEach(() => wrapper = mount(
      <ImportModuleFromGitHub
        libraryOpen={true}
        moduleAdded={moduleAdded}
        api={api}
        isReadOnly={false}
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

    it('Import button makes API call', () => { 
      //open modal
      modalLink.simulate('click');
      // find modal, wrap it
      let modal_element = document.getElementsByClassName('modal-dialog');
      let modal = new ReactWrapper(modal_element[0], true)
      // find Import button and click it
      let importButton = modal.find('.button-blue');
      expect(importButton).toHaveLength(1);
      importButton.simulate('click');
      // check on function calls
      expect(api.importFromGithub.mock.calls.length).toBe(1);
    });
  });

  describe('Library closed', () => {

    beforeEach(() => wrapper = mount(
      <ImportModuleFromGitHub
        libraryOpen={true}
        moduleAdded={moduleAdded}
        api={api}     
        isReadOnly={false}
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
      // thirs rendering of modal element, so length of 3
      expect(modal_element.length).toBe(3);
      let modal = new ReactWrapper(modal_element[0], true)
      expect(modal).toMatchSnapshot();
      expect(modal.find('.dialog-body')).toHaveLength(1);
    });

  });

});


