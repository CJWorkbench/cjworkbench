/**
 * Testing Stories:
 * -Renders library-open version
 *    -Clicking on category will toggle collapse of module list
 * -Renders library-closed version
 *    -Mouse enter on category will toggle display of module list
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
  
    it('Click events on a category will toggle its module list display', () => { 
      // find category card
      let category = wrapper.find('.first-level');
      expect(category).toHaveLength(1);
      // find Collapse component
      let moduleList = wrapper.find('Collapse');
      expect(moduleList).toHaveLength(1);
      // access isOpen property of Collapse, check that it is closed
      expect(moduleList.get(0).props.isOpen).toBe(false);
      // simulate a click on category
      category.simulate('click');
      expect(wrapper).toMatchSnapshot();      
      // check isOpen, should be open
      expect(moduleList.get(0).props.isOpen).toBe(true);
      // another click
      category.simulate('click');      
      // isOpen should be closed
      expect(moduleList.get(0).props.isOpen).toBe(false);
    });

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
      // check for presence of Modules
      expect(wrapper.find('.ml-module-card')).toHaveLength(2);
    });

    it('Mouse enter events on a category will toggle its module list display', () => { 
      // find category card
      let category = wrapper.find('.first-level');
      expect(category).toHaveLength(1);
      // find module list
      let moduleList = wrapper.find('.ml-list-mini');
      expect(moduleList).toHaveLength(1);
      // access styles of module list
      let listStyle = moduleList.get(0).style._values;
      // check that module list is not displayed
      expect(listStyle).toEqual({'display': 'none'});
      // simulate a mouse enter
      category.simulate('mouseEnter');
      expect(wrapper).toMatchSnapshot();   
      // check that module list is displayed
      expect(listStyle).toEqual({'display': 'block'});
      // mouse enter again to close
      category.simulate('mouseEnter');
      expect(listStyle).toEqual({'display': 'none'});
    });
  });
});