/**
 * Testing Stories:
 * -In not-read-only, renders <ModuleLibraryOpen> by default in not-read-only
 * -When read-only, renders <ModuleLibraryClosed> without modules.
 *
 */

import React from 'react'
import ModuleLibrary  from './ModuleLibrary'
import { mount, ReactWrapper } from 'enzyme'
import { jsonResponseMock, emptyAPI } from './utils'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'

describe('ModuleLibrary', () => {

  var wrapper;
  var addModule =  () => {};
  var dropModule =  () => {};
  var workflow = {
    "id":15,
    "name":"What a workflow!",
  };
  var modules = [
    {
      "id":1,
      "name":"Chartbuilder",
      "category":"Visualize",
      "description":"Create line, column and scatter plot charts.",
      "icon":"chart"
    },
    {
      "id":2,
      "name":"Load from Facebork",
      "category":"Add data",
      "description":"Import from your favorite snowshall media",
      "icon":"url"
    },
    {
      "id":3,
      "name":"Load from Enigma",
      "category":"Add data",
      "description":"Connect a dataset from Enigma's collection via URL.",
      "icon":"url"
    },
    {
      "id":4,
      "name":"Other Module 1",
      "category":"other category",    // test modules outside the predefined categories
      "icon":"url"
    },
    {
      "id":5,
      "name":"Other Module 2",
      "category":"x category",
      "icon":"url"
    },
    {
      "id":6,
      "name":"Other Module 3",
      "category":"other category",
      "icon":"url"
    },
  ];

  var api = {};
  var libraryOpen = true;
  var setLibraryOpen = function(libraryOpen) {
      libraryOpen = libraryOpen;
  };

  describe('Not Read-only', () => {

    beforeEach(() => {
      api = {
        getModules: jsonResponseMock(modules),
        setWfLibraryCollapse: jest.fn()
      };
      wrapper = mount(
        <DragDropContextProvider backend={HTML5Backend}>
          <ModuleLibrary
            addModule={addModule}
            dropModule={dropModule}
            api={api}
            workflow={workflow}
            isReadOnly={false}
            libraryOpen={libraryOpen}
            setLibraryOpen={setLibraryOpen}
          />
        </DragDropContextProvider>);
    });
    afterEach(() => wrapper.unmount());

    it('Renders in open state and loads modules', (done) => {
      expect(wrapper).toMatchSnapshot();

      expect(api.getModules.mock.calls.length).toBe(1);   // should have called API for its data on componentDidMount
      expect(wrapper.find('.module-library-open')).toHaveLength(1);  // check that Library is open

      // let json promise resolve (wait for modules to load)
      setImmediate( () => {

        // Sadly this does not work: https://github.com/airbnb/enzyme/issues/431
        // // Ensure all modules in each category are contiguous
        // var modules = wrapper.childAt(0).state('items');
        // var seenCats = [];
        // var currentCat = null;
        // for (var m of modules) {
        //   if (m.category != currentCat) {                       // different cat than last module
        //     expect(seenCats.includes(m.category)).toBeFalsy();  // should not repeat category
        //     seenCats.push(m.category);
        //   }
        //   currentCat = m.category;
        // }

        expect(wrapper).toMatchSnapshot();

        expect(wrapper.find('.ml-cat')).toHaveLength(4);                      // module categories
        expect(wrapper.find('.ml-list .ml-icon-container')).toHaveLength(6);  // modules

        done();
      });
    });

    it('Clicking on arrow will invoke API to toggle collapse', (done) => {
      // let json promise resolve (wait for modules to load)
      setImmediate( () => {
        let arrow = wrapper.find('.close-open-toggle');
        expect(arrow).toHaveLength(1);
        arrow.simulate('click');
        expect(api.setWfLibraryCollapse.mock.calls.length).toBe(1);
        done();
      });
    });

  });

  describe('Read-only', () => {

    beforeEach(() => {
      api = {
        getModules: jsonResponseMock(modules),
        setWfLibraryCollapse: jest.fn()
      };
      libraryOpen = false;
      wrapper = mount(
        <DragDropContextProvider backend={HTML5Backend}>
          <ModuleLibrary
            addModule={addModule}
            dropModule={dropModule}
            api={api}
            workflow={workflow}
            isReadOnly={true}
            libraryOpen={libraryOpen}
            setLibraryOpen={setLibraryOpen}
          />
        </DragDropContextProvider>
      );
    });
    afterEach(() => wrapper.unmount());

    it('Renders in closed state, without modules', () => {
      expect(wrapper).toMatchSnapshot();
      // should NOT call getModules
      expect(api.getModules.mock.calls.length).toBe(0);
      // check that Library is closed
      expect(wrapper.find('.module-library-closed')).toHaveLength(1);
    });

  });

});
