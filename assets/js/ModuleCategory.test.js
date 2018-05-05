/**
 * Testing Stories:
 * -Renders library-open version
 *    -Clicking on category will toggle collapse of module list
 * -Renders library-closed version
 *    -Mouse enter on category will show module list
 *    -Mouse leave on category will hide module list
 *    -Mouse leave on module list will hide module list
 * 
 */

import React from 'react'
import ModuleCategory from './ModuleCategory'
import Module from './Module'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'

describe('ModuleCategory ', () => {

  var wrapper;
  var setOpenCategory;
  var modules;

  describe('Library open', () => {

    beforeEach(() => {
      setOpenCategory = jest.fn();
      modules = [
        <Module
          key={"First Module"}
          name={"First Module"}
          icon={"add"}
          id={88}
          addModule={() => {}}
          dropModule={() => {}}
          isReadOnly={false}
          setOpenCategory={setOpenCategory}
          libraryOpen={true}
        />,
        <Module
          key={"Second Module"}
          name={"Second Module"}
          icon={"url"}
          id={101}
          addModule={() => {}}
          dropModule={() => {}}
          isReadOnly={false}
          setOpenCategory={setOpenCategory}
          libraryOpen={true}
        />
      ];
      wrapper = mount(
        <DragDropContextProvider backend={HTML5Backend}>
          <ModuleCategory
            name={"Add Data"}
            modules={modules}
            isReadOnly={false}
            setOpenCategory={setOpenCategory}
            libraryOpen={true}
            collapsed={false}
          />
        </DragDropContextProvider>
      );
    });
    afterEach(() => {
      wrapper.unmount();
    });

    it('Renders with list of Module components', () => {
      expect(wrapper).toMatchSnapshot();
      expect(wrapper.find('.ml-module-card')).toHaveLength(2);
    });

  });


  describe('Library closed, category collapsed ', () => {

    beforeEach(() => {
      setOpenCategory = jest.fn();
      modules = [
        <Module
          key={"First Module"}
          name={"First Module"}
          icon={"add"}
          id={88}
          addModule={() => {}}
          dropModule={() => {}}
          isReadOnly={false}
          setOpenCategory={setOpenCategory}
          libraryOpen={false}
        />,
        <Module
          key={"Second Module"}
          name={"Second Module"}
          icon={"url"}
          id={101}
          addModule={() => {}}
          dropModule={() => {}}
          isReadOnly={false}
          setOpenCategory={setOpenCategory}
          libraryOpen={false}
        />
      ];
      wrapper = mount(
        <DragDropContextProvider backend={HTML5Backend}>
          <ModuleCategory
            name={"Add data"}
            modules={modules}
            isReadOnly={false}
            collapsed={true}
            setOpenCategory={setOpenCategory}
            libraryOpen={false}
          />
        </DragDropContextProvider>
      )
    });
    afterEach(() => {
      wrapper.unmount();
    });

    it('Renders with category icon, but without list of Module components', () => {
      expect(wrapper).toMatchSnapshot();
      // check that correct icon is displayed for "Add Data"
      expect(wrapper.find('.icon-database')).toHaveLength(1);
      // check for absence of Modules
      expect(wrapper.find('.ml-module-card')).toHaveLength(0);
    });

    it('Mouse enter events on a category will open module list', () => {
      // find category card
      let category = wrapper.find('.ML-cat');
      expect(category).toHaveLength(1);
      // ensure absence of module list
      let moduleList = wrapper.find('.ml-list-mini');
      expect(moduleList).toHaveLength(0);
      // mouse enters category
      category.simulate('mouseEnter');
      // check: setOpenCategory() called from props
      expect(setOpenCategory.mock.calls.length).toBe(1);
    });
  });

  describe('Library closed, category open', () => {

    beforeEach(() => {
      setOpenCategory = jest.fn();
      modules = [
        <Module
          key={"First Module"}
          name={"First Module"}
          icon={"add"}
          id={88}
          addModule={() => {}}
          dropModule={() => {}}
          isReadOnly={false}
          setOpenCategory={setOpenCategory}
          libraryOpen={false}
        />,
        <Module
          key={"Second Module"}
          name={"Second Module"}
          icon={"url"}
          id={101}
          addModule={() => {}}
          dropModule={() => {}}
          isReadOnly={false}
          setOpenCategory={setOpenCategory}
          libraryOpen={false}
        />
      ];
      wrapper = mount(
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
      )
    });
    afterEach(() => {
      wrapper.unmount();
    });

    it('Renders with list of Module components', () => {
      expect(wrapper).toMatchSnapshot();
      // check for presence of Modules
      expect(wrapper.find('.ml-module-card')).toHaveLength(2);
    });

    it('Mouse leave events on a category will close module list', () => {
      // find category card
      let category = wrapper.find('.ML-cat');
      expect(category).toHaveLength(1);
      // ensure presence of module list
      let moduleList = wrapper.find('.ml-list-mini');
      expect(moduleList).toHaveLength(1);
      category.simulate('mouseLeave');
      expect(setOpenCategory.mock.calls.length).toBe(1);
    });

    it('Mouse leave events on module list will close list display', () => {
      let moduleList = wrapper.find('.ml-list-mini');
      moduleList.simulate('mouseLeave');
      expect(setOpenCategory.mock.calls.length).toBe(1);
    });
  });
});
