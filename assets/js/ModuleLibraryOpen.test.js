/**
 * Testing Stories:
 * -Renders full menu with <ModuleSearch>, <ModuleCategories>, <AddNotificationButton>,
 *    and <ImportModuleFromGitHub> components
 * -Toggle arrow will invoke toggleLibrary() from props
 *
 */

import React from 'react'
import ModuleLibraryOpen  from './ModuleLibraryOpen'
import { shallowWithStubbedStore } from './test-utils'

describe('ModuleLibraryOpen ', () => {
  let wrapper

  let toggleLibrary
  beforeEach(() => {
    toggleLibrary = jest.fn()
  })

  const modules = [
    {
      "id":4,
      "name":"Load from Enigma",
      "category":"Add data",
      "icon":"url",
    },
    {
      "id":10,
      "name":"Filter by Text",
      "category":"Filter",
      "icon":"filter",
    },
  ]

  beforeEach(() => {
    wrapper = shallowWithStubbedStore(
      <ModuleLibraryOpen
        api={{}}
        workflow={{}}
        libraryOpen={true}
        isReadOnly={false}
        modules={modules}
        addModule={() => {}}
        dropModule={() => {}}
        moduleAdded={() => {}}
        toggleLibrary={toggleLibrary}
        openCategory={"Add Data"}
        setOpenCategory={() => {}}
        />
    )
  })

  it('matches snapshot', () => {
    expect(wrapper).toMatchSnapshot()
  })

  it('Clicking arrow will invoke Toggle Library function', () => {
    const arrow = wrapper.find('.ML-toggle')
    expect(arrow).toHaveLength(1)
    arrow.simulate('click')
    expect(toggleLibrary.mock.calls.length).toBe(1)
  })
})
