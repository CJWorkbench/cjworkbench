/**
 * Testing Stories:
 * -In not-read-only, renders <ModuleLibraryOpen> by default in not-read-only
 * -When read-only, renders <ModuleLibraryClosed> without modules.
 *
 */

import React from 'react'
import ModuleLibrary  from './ModuleLibrary'
import { mount } from 'enzyme'
import { jsonResponseMock, emptyAPI } from './utils'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


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
    "id":4,
    "name":"Load from Enigma",
    "category":"Add data",
    "description":"Connect a dataset from Enigma's collection via URL.",
    "icon":"url"
  }
];
var api = {
  getModules: jsonResponseMock(modules),
};
var libraryOpen = true;
var setLibraryOpen = function(libraryOpen) {
    libraryOpen = libraryOpen;
}

describe('ModuleLibrary', () => {

  describe('Not Read-only', () => {

    beforeEach(() => wrapper = mount(
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
      </DragDropContextProvider>
    ));
    afterEach(() => wrapper.unmount());

    it('Renders in open state and loads modules', (done) => {
      expect(wrapper).toMatchSnapshot();
      // should have called API for its data on componentDidMount
      expect(api.getModules.mock.calls.length).toBe(1);
      // check that Library is open
      expect(wrapper.find('.module-library-open')).toHaveLength(1);
      // let json promise resolve (wait for modules to load)
      setImmediate( () => {
        expect(wrapper).toMatchSnapshot();
        // check that module categories have loaded
        expect(wrapper.find('.ml-cat')).toHaveLength(2);
        // check that modules have loaded
        expect(wrapper.find('.ml-list .ml-icon-container')).toHaveLength(3);
        done();
      });
    });

  });

  describe('Read-only', () => {

    beforeEach(() => {
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
    )});
    afterEach(() => wrapper.unmount());

    it('Renders in closed state, without modules', () => {
      expect(wrapper).toMatchSnapshot();
      // should NOT call getModules (one call from previous test)
      expect(api.getModules.mock.calls.length).toBe(1);
      // check that Library is closed
      expect(wrapper.find('.module-library-closed')).toHaveLength(1);
    });

  });

});
