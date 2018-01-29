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
  const setOpenCategory = jest.fn();
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
  
  describe('Library open, category collapsed', () => {
  
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <ModuleCategory
          name={"Add Data"}
          modules={modules}
          isReadOnly={false}
          collapsed={true} 
          setOpenCategory={setOpenCategory} 
          libraryOpen={true}
        />
      </DragDropContextProvider>
    ));
    afterEach(() => wrapper.unmount());    
  
    it('Renders with list of Module components', () => { 
      expect(wrapper).toMatchSnapshot();
      expect(wrapper.find('.ml-module-card')).toHaveLength(2);
    });
  
    it('Clicking an collapsed category will expand it', () => { 
      let category = wrapper.find('.first-level');
      expect(category).toHaveLength(1);
      let moduleList = wrapper.find('Collapse');
      expect(moduleList).toHaveLength(1);
      expect(moduleList.get(0).props.isOpen).toBe(false);
      category.simulate('click');
      expect(setOpenCategory.mock.calls.length).toBe(1); 
    });
  });

  describe('Library open, category open', () => {
  
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <ModuleCategory
          name={"Add Data"}
          modules={modules}
          isReadOnly={false}
          collapsed={false} 
          setOpenCategory={setOpenCategory} 
          libraryOpen={true}
        />
      </DragDropContextProvider>
    ));
    afterEach(() => wrapper.unmount());    
  
    it('Clicking an open category will collapse it', () => { 
      // find category card
      let category = wrapper.find('.first-level');
      expect(category).toHaveLength(1);
      // find Collapse component
      let moduleList = wrapper.find('Collapse');
      expect(moduleList).toHaveLength(1);
      // access isOpen property of Collapse, check that it is closed
      expect(moduleList.get(0).props.isOpen).toBe(true);
      // simulate a click on category
      category.simulate('click');
      // check: was setOpenCategory() called from props?
      expect(setOpenCategory.mock.calls.length).toBe(2); // called once before
    });
  });

  describe('Library closed, category collapsed ', () => {
  
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <ModuleCategory
          name={"Add Data"}
          modules={modules}
          isReadOnly={false}
          collapsed={true} 
          setOpenCategory={setOpenCategory} 
          libraryOpen={false}
        />
      </DragDropContextProvider>
    ));
    afterEach(() => wrapper.unmount());    
  
    it('Renders without list of Module components', () => { 
      expect(wrapper).toMatchSnapshot();
      // check for absence of Modules
      expect(wrapper.find('.ml-module-card')).toHaveLength(0);
    });

    it('Mouse enter events on a category will open module list', () => { 
      // find category card
      let category = wrapper.find('.first-level');
      expect(category).toHaveLength(1);
      // ensure absence of module list
      let moduleList = wrapper.find('.ml-list-mini');
      expect(moduleList).toHaveLength(0);
      // mouse enters category
      category.simulate('mouseEnter');
      // check: setOpenCategory() called from props
      expect(setOpenCategory.mock.calls.length).toBe(3); // called twice before
    });
  });

  describe('Library closed, category collapsed ', () => {
  
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <ModuleCategory
          name={"Add Data"}
          modules={modules}
          isReadOnly={false}
          collapsed={false} 
          setOpenCategory={setOpenCategory} 
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

    it('Mouse enter events on a category will close module list', () => { 
      // find category card
      let category = wrapper.find('.first-level');
      expect(category).toHaveLength(1);
      // ensure presence of module list
      let moduleList = wrapper.find('.ml-list-mini');
      expect(moduleList).toHaveLength(1);
      category.simulate('mouseEnter');
      expect(setOpenCategory.mock.calls.length).toBe(4);
    });

    it('Mouse leave events on module list will close list display', () => { 
      let category = wrapper.find('.first-level');
      let moduleList = wrapper.find('.ml-list-mini');
      moduleList.simulate('mouseLeave');
      expect(setOpenCategory.mock.calls.length).toBe(5); 
    });
  });
});