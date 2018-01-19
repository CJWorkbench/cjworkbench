/**
 * Testing Stories:
 * -Renders library-open version, which has collapsible list of Module components
 * -Renders library-closed version, "
 * -When one category is expanded, others collapse
 * 
 * Note: holding on collapse tests until after library-closed version 
 *    has hover-based collapse implemented 
 */

import React from 'react'
import ModuleCategory from './ModuleCategory'
import Module from './Module'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'

describe('ModuleCategory ', () => {
  
  var wrapper;  
  var modules = [
    <Module
      key={"First Module"}
      name={"First Module"}
      icon={"add"}
      id={88}
      addModule={() => {}}
      dropModule={() => {}}
    />,
    <Module
      key={"Second Module"}
      name={"Second Module"}
      icon={"url"}
      id={101}
      addModule={() => {}}
      dropModule={() => {}}
    />
  ];
  
  describe('Library open ', () => {
  
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <ModuleCategory
          name={"Add Data"}
          modules={modules}
          isReadOnly={false}
          collapsed={true} 
          setOpenCategory={() => {}} 
          libraryOpen={true}
        />
      </DragDropContextProvider>
    ));
    afterEach(() => wrapper.unmount());    
  
    it('Renders with list of Module components', () => { 
      expect(wrapper).toMatchSnapshot();

      // check for list of Modules
      expect(wrapper.find('.ml-module-card')).toHaveLength(2);
    });
  
    // it('Clicking on a category will expand it', () => { 
    //   expect(true).toBe(true);
    // });

    // it('Expanding one category will collapse the others', () => { 
    //   expect(true).toBe(true);
    // });

  });

  describe('Library closed ', () => {
  
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <ModuleCategory
          name={"Add Data"}
          modules={modules}
          isReadOnly={false}
          collapsed={true} 
          setOpenCategory={() => {}} 
          libraryOpen={false}
        />
      </DragDropContextProvider>
    ));
    afterEach(() => wrapper.unmount());    
  
    it('Renders with list of Module components', () => { 
      expect(wrapper).toMatchSnapshot();
      
      // check for list of Modules
      expect(wrapper.find('.ml-module-card')).toHaveLength(2);
    });
  
    // it('Hovering a category will expand it', () => { 
    //   expect(true).toBe(true);
    // });

    // it('Mouse leaving a category will collapse it', () => { 
    //   expect(true).toBe(true);
    // });
      
  });
  
      
});