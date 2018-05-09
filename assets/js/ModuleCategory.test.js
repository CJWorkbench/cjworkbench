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
import { shallowWithStubbedStore } from './test-util'

describe('ModuleCategory ', () => {
  let wrapper
  let setOpenCategory
  const modules = [
    { id: 88, icon: 'add', name: 'First Module' },
    { id: 101, icon: 'url', name: 'Second Module' },
  ]

  beforeEach(function() {
    setOpenCategory = jest.fn()
  })

  describe('Library open', () => {
    beforeEach(() => {
      wrapper = shallowWithStubbedStore(
        <ModuleCategory
          name={"Add Data"}
          modules={modules}
          isReadOnly={false}
          setOpenCategory={setOpenCategory}
          libraryOpen={true}
          collapsed={false}
          />
      )
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('Renders with list of Module components', () => {
      expect(wrapper.find(Module)).toHaveLength(2)
    })
  })

  describe('Library closed, category collapsed ', () => {
    beforeEach(() => {
      wrapper = shallowWithStubbedStore(
        <ModuleCategory
          name={"Add data"}
          modules={modules}
          isReadOnly={false}
          collapsed={true}
          setOpenCategory={setOpenCategory}
          libraryOpen={false}
          />
      )
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot();
    })

    it('renders with category icon, but without list of Module components', () => {
      // check that correct icon is displayed for "Add Data"
      expect(wrapper.find('.icon-database')).toHaveLength(1)
      // check for absence of Modules
      expect(wrapper.find('.ml-module-card')).toHaveLength(0)
    })

    it('opens module list on category mouseenter', () => {
      // find category card
      let category = wrapper.find('.ML-cat')
      expect(category).toHaveLength(1)
      // ensure absence of module list
      let moduleList = wrapper.find('.ml-list-mini')
      expect(moduleList).toHaveLength(0)
      // mouse enters category
      category.simulate('mouseEnter')
      // check: setOpenCategory() called from props
      expect(setOpenCategory.mock.calls.length).toBe(1)
    })
  })

  describe('Library closed, category open', () => {
    beforeEach(() => {
      wrapper = shallowWithStubbedStore(
        <ModuleCategory
          name={"Add Data"}
          modules={modules}
          isReadOnly={false}
          collapsed={false}
          setOpenCategory={setOpenCategory}
          libraryOpen={false}
        />
      )
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot();
    })

    it('renders with list of Module components', () => {
      expect(wrapper.find(Module)).toHaveLength(2)
    })

    it('closes module list on category mouseleave', () => {
      // find category card
      const category = wrapper.find('.ML-cat')
      expect(category).toHaveLength(1)
      expect(wrapper.find('.ml-list-mini')).toHaveLength(1)
      category.simulate('mouseLeave')
      expect(setOpenCategory).toHaveBeenCalledWith(null)
    })

    it('closes module list on .ml-list-mini mouseleave', () => {
      let moduleList = wrapper.find('.ml-list-mini')
      moduleList.simulate('mouseLeave')
      expect(setOpenCategory).toHaveBeenCalledWith(null)
    })
  })
})
