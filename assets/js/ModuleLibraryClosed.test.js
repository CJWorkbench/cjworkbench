/**
 * Testing Stories:
 * -Renders collapsed menu with <ModuleCategories>, <AddNotificationButton>, 
 *    and <ImportModuleFromGitHub> components
 * -Toggle arrow will invoke toggleLibrary() from props
 * 
 */

import React from 'react'
import ModuleLibraryClosed  from './ModuleLibraryClosed'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('ModuleLibraryClosed', () => {

  var wrapper;  
  var openLibrary = jest.fn();
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

  beforeEach(() => wrapper = mount(
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
        openCategory={"Add Data"} 
        setOpenCategory={() => {}}
      />
    </DragDropContextProvider>
  ));
  afterEach(() => wrapper.unmount());  

  it('Renders all subcomponents', () => { 
    expect(wrapper).toMatchSnapshot(); 
  });

  it('Clicking arrow will invoke Open Library function', () => { 
    let arrow = wrapper.find('.close-open-toggle');
    expect(arrow).toHaveLength(1);
    arrow.simulate('click');
    expect(openLibrary.mock.calls.length).toBe(1);
  });
      
});