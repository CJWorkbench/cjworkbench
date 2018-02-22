/**
 * Testing Stories:
 * -Renders collapsed menu with <ModuleCategories>, <AddNotificationButton>,
 *    and <ImportModuleFromGitHub> components
 * -Toggle arrow will invoke toggleLibrary() from props
 * 
 * TODO:
 * -Read only state: click below header to open modal
 *    -modal goes to sign in page
 *
 */

import React from 'react'
import ModuleLibraryClosed  from './ModuleLibraryClosed'
import { mount, ReactWrapper } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('ModuleLibraryClosed', () => {

  var wrapper;
  var openLibrary; 
  var modal;
  var items = [
    {
      "id":4,
      "name":"Load from Enigma",
      "category":"Add data",
      "description":"Connect a dataset from Enigma's collection via URL.",
      "link":"",
      "author":"Workbench",
      "icon":"url"
    },
    {
      "id":10,
      "name":"Filter by Text",
      "category":"Filter",
      "description":"Filter rows by matching text in specific columns.",
      "link":"",
      "author":"Workbench",
      "icon":"filter"
    }
  ];

  describe('NOT Read-Only', () => {

    beforeEach(() => {
      openLibrary = jest.fn()
      wrapper = mount(
        <DragDropContextProvider backend={HTML5Backend}>
          <ModuleLibraryClosed
            api={{}}
            libraryOpen={true}
            isReadOnly={false}
            items={items}
            addModule={() => {}}
            dropModule={() => {}}
            moduleAdded={() => {}}
            openLibrary={openLibrary}
            openCategory={"Add data"}
            setOpenCategory={() => {}}
          />
        </DragDropContextProvider>
      )
    });
    afterEach(() => {
      wrapper.unmount();
    });

    it('Renders', () => {
      expect(wrapper).toMatchSnapshot();
    });

    it('Clicking arrow will invoke Open Library function', () => {
      let arrow = wrapper.find('.library-closed--toggle');
      expect(arrow).toHaveLength(1);
      arrow.simulate('click');
      expect(openLibrary.mock.calls.length).toBe(1);
    });

  });


  describe('Read-Only', () => {

    beforeEach(() => {
      openLibrary = jest.fn();
      wrapper = mount(
        <DragDropContextProvider backend={HTML5Backend}>
          <ModuleLibraryClosed
            api={{}}
            libraryOpen={true}
            isReadOnly={true}
            items={items}
            addModule={() => {}}
            dropModule={() => {}}
            moduleAdded={() => {}}
            openLibrary={openLibrary}
            openCategory={"Add data"}
            setOpenCategory={() => {}}
          />
        </DragDropContextProvider>
      );
    });
    afterEach(() => {
      wrapper.unmount();
    });

    it('Renders', () => {
      expect(wrapper).toMatchSnapshot();
    });

    it('Clicking below header will open modal with link to Sign-In page', () => {
      let importLink = wrapper.find('ImportModuleFromGitHub');
      importLink.simulate('click');
      // The insides of the Modal are a "portal", that is, attached to root of DOM, not a child of Wrapper
      // So find them, and make a new Wrapper
      // Reference: "https://github.com/airbnb/enzyme/issues/252"
      let modal_element = document.getElementsByClassName('test-signin-modal');
      modal = new ReactWrapper(modal_element[0], true)
      // check for link to sign-in page
      expect(modal.find('[href="/account/login"]')).toHaveLength(1);
    });

  });

});
