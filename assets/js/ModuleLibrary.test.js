/**
 * Testing Stories:
 * -In not-read-only, renders <ModuleLibraryOpen> by default in not-read-only
 * -When read-only, renders <ModuleLibraryClosed> without modules.
 *
 */

import React from 'react'
import { ModuleLibrary } from './ModuleLibrary'
import { shallow } from 'enzyme'
import { jsonResponseMock, emptyAPI } from './utils'

describe('ModuleLibrary', () => {
  let wrapper
  let api

  let workflow = {
    "id":15,
    "name":"What a workflow!",
  }
  const modules = [
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
      "id":3,
      "name":"Load from Enigma",
      "category":"Add data",
      "description":"Connect a dataset from Enigma's collection via URL.",
      "icon":"url"
    },
    {
      "id":4,
      "name":"Other Module 1",
      "category":"other category",    // test modules outside the predefined categories
      "icon":"url"
    },
    {
      "id":5,
      "name":"Other Module 2",
      "category":"x category",
      "icon":"url"
    },
    {
      "id":6,
      "name":"Other Module 3",
      "category":"other category",
      "icon":"url"
    },
  ]

  let stubs
  beforeEach(() => {
    stubs = {
      setLibraryOpen: jest.fn(),
      addModule: jest.fn(),
      dropModule: jest.fn(),
      setWfLibraryCollapse: jest.fn(),
    }
  })

  describe('Not Read-only', () => {
    beforeEach(() => {
      api = {
        getModules: jsonResponseMock(modules),
        setWfLibraryCollapse: jest.fn(),
      }
      wrapper = shallow(
        <ModuleLibrary
          {...stubs}
          api={api}
          workflow={workflow}
          isReadOnly={false}
          libraryOpen={true}
          />
      )
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('loads modules', (done) => {
      const moduleLibraryOpen = wrapper.find('ModuleLibraryOpen')
      expect(moduleLibraryOpen).toHaveLength(1) // is open
      expect(moduleLibraryOpen.props().modules).toHaveLength(0) // no modules by default

      expect(api.getModules).toHaveBeenCalled()

      // let json promise resolve (wait for modules to load)
      setImmediate(() => {
        wrapper.update()
        expect(wrapper.find('ModuleLibraryOpen').props().modules).toEqual(modules)
        done()
      })
    })
  })

  describe('Read-only', () => {
    beforeEach(() => {
      wrapper = shallow(
        <ModuleLibrary
          {...stubs}
          api={api}
          workflow={workflow}
          isReadOnly={true}
          libraryOpen={true}
          />
      )
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('loads modules', (done) => {
      const moduleLibraryClosed = wrapper.find('ModuleLibraryClosed')
      expect(moduleLibraryClosed).toHaveLength(1) // is open
      expect(moduleLibraryClosed.props().modules).toHaveLength(0) // no modules by default

      expect(api.getModules).toHaveBeenCalled()

      // let json promise resolve (wait for modules to load)
      setImmediate(() => {
        wrapper.update()
        expect(wrapper.find('ModuleLibraryClosed').props().modules).toEqual(modules)
        done()
      })
    })
  })
})
