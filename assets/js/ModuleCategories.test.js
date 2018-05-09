/**
 * Testing Stories:
 * -Renders list of <ModuleCategory> components
 *
 */

import React from 'react'
import ModuleCategories  from './ModuleCategories'
import { shallow } from 'enzyme'


describe('ModuleCategories ', () => {
  let wrapper
  const modules = [
    {
      "id":4,
      "name":"Load from Enigma",
      "category":"Add data",
      "icon":"url"
    },
    {
      "id":10,
      "name":"Filter by Text",
      "category":"Filter",
      "icon":"filter"
    },
    {
      "id":11,
      "name":"Filter by Something Else",
      "category":"Filter",
      "icon":"filter"
    },
  ]

  describe('Library open ', () => {
    beforeEach(() => {
      wrapper = shallow(
        <ModuleCategories
          openCategory={"Add data"}
          setOpenCategory={() => {}}
          libraryOpen={true}
          isReadOnly={false}
          addModule={() => {}}
          dropModule={() => {}}
          modules={modules}
        />
      )
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('renders ModuleCategory components', () => {
      function describe(mc) {
        return {
          category: mc.name,
          collapsed: mc.collapsed,
          names: mc.modules.map(m => m.name),
        }
      }
      expect(wrapper.find('ModuleCategory').map(mc => describe(mc.props()))).toEqual([
        { category: 'Add data', collapsed: false, names: [ 'Load from Enigma' ] },
        { category: 'Filter', collapsed: true, names: [ 'Filter by Text', 'Filter by Something Else' ] },
      ])
    })
  })

  describe('Library closed ', () => {
    beforeEach(() => {
      wrapper = shallow(
        <ModuleCategories
          openCategory={"Add data"}
          setOpenCategory={() => {}}
          libraryOpen={false}
          isReadOnly={false}
          addModule={() => {}}
          dropModule={() => {}}
          modules={modules}
          />
      )
    })

    it('renders children as closed', () => {
      expect(wrapper.find('ModuleCategory').map(mc => mc.props().libraryOpen)).toEqual([ false, false ])
    })
  })
})
