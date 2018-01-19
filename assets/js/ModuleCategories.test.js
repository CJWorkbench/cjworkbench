/**
 * Testing Stories:
 * -Renders list of <ModuleCategory> components
 * 
 */

import React from 'react'
import ModuleCategories  from './ModuleCategories'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('ModuleCategories ', () => {
  
  var wrapper;  
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
  
  describe('Library open ', () => {

    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <ModuleCategories
          openCategory={"Add Data"} 
          setOpenCategory={() => {}}
          libraryOpen={true}
          isReadOnly={false}            
          addModule={() => {}}
          dropModule={() => {}}
          items={items}
        />
      </DragDropContextProvider>
    ));

    afterEach(() => wrapper.unmount());    
  
    it('Renders with list of ModuleCategory components', () => { 
      expect(wrapper).toMatchSnapshot();
    });

  });

  describe('Library closed ', () => {
  
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <ModuleCategories
          openCategory={"Add Data"} 
          setOpenCategory={() => {}}
          libraryOpen={false}
          isReadOnly={false}            
          addModule={() => {}}
          dropModule={() => {}}
          items={items}
        />
      </DragDropContextProvider>
    ));

    afterEach(() => wrapper.unmount());    
  
    it('Renders with list of ModuleCategory components', () => { 
      expect(wrapper).toMatchSnapshot();
    });
  
  });
      
});
