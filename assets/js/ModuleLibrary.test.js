/**
 * Testing Stories:
 * -Renders <ModuleLibraryOpen> by default in not-read-only 
 * -Renders <ModuleLibraryClosed> when ...
 * -Queries mock API to set 'items' state with sorted modules
 * -In read-only state, renders closed
 * -??? (TBD)
 */

import React from 'react'
import ModuleLibrary  from './ModuleLibrary'
import { mount, shallow } from 'enzyme'
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


it('ModuleLibrary renders open when not read-only, with list of module categories', (done) => {
  expect(true).toBe(true);

  wrapper = mount(
    <DragDropContextProvider backend={HTML5Backend}>
      <ModuleLibrary
        addModule={addModule}
        dropModule={dropModule}
        api={api}
        workflow={workflow}
        isReadOnly={false}
      />
    </DragDropContextProvider>
  );

  expect(wrapper).toMatchSnapshot();

  // should call API for its data on componentDidMount
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

// *** How to work around restriction of only one backend at a time? ***

// it('ModuleLibrary renders closed when read-only', () => {
//   wrapper = mount(
//     <DragDropContextProvider backend={HTML5Backend}>
//       <ModuleLibrary
//         addModule={addModule}
//         dropModule={dropModule}
//         api={api}
//         workflow={workflow}
//         isReadOnly={true}
//       />
//     </DragDropContextProvider>
//   );

//   expect(wrapper).toMatchSnapshot();

//   // check that Library is closed
//   expect(wrapper.find('.module-library-collapsed')).toHaveLength(1);

// });


// it('ModuleLibrary may be toggled between open and closed states', () => {


// });