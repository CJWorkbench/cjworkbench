/**
 * Testing Stories:
 * -Renders collapsed menu with <ModuleCategories>
 *    and <ImportModuleFromGitHub> components
 * -Toggle arrow will invoke toggleLibrary() from props
 *
 * TODO:
 * -Read only state: click below header to open modal
 *    -modal goes to sign in page
 *
 */

import React from 'react'
import ModuleLibraryClosed from './ModuleLibraryClosed'
import { mount, ReactWrapper } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'
import { Provider } from 'react-redux'
import { createStore } from 'redux'

describe('ModuleLibraryClosed', () => {
  let wrapper
  let openLibrary
  let store

  const modules = [
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
  ]

  beforeEach(() => {
    openLibrary = jest.fn()
    store = createStore(() => ({}), {})
    //store = createStore((state, action) => Object.assign({}, state, action), {})
  })

  describe('NOT Read-Only', () => {
    beforeEach(() => {
      wrapper = mount(
        <Provider store={store}>
          <DragDropContextProvider backend={HTML5Backend}>
            <ModuleLibraryClosed
              api={{}}
              libraryOpen={true}
              isReadOnly={false}
              modules={modules}
              addModule={() => {}}
              dropModule={() => {}}
              openLibrary={openLibrary}
              openCategory={"Add data"}
              setOpenCategory={() => {}}
            />
          </DragDropContextProvider>
        </Provider>
      )
    });
    afterEach(() => {
      wrapper.unmount()
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('invokes Open Library on arrow click', () => {
      let arrow = wrapper.find('.library-closed--toggle')
      expect(arrow).toHaveLength(1)
      arrow.simulate('click')
      expect(openLibrary).toHaveBeenCalled()
    })
  })

  describe('Read-Only', () => {
    beforeEach(() => {
      wrapper = mount(
        <Provider store={store}>
          <DragDropContextProvider backend={HTML5Backend}>
            <ModuleLibraryClosed
              api={{}}
              libraryOpen={true}
              isReadOnly={true}
              modules={modules}
              addModule={() => {}}
              dropModule={() => {}}
              moduleAdded={() => {}}
              openLibrary={openLibrary}
              openCategory={"Add data"}
              setOpenCategory={() => {}}
            />
          </DragDropContextProvider>
        </Provider>
      )
    })
    afterEach(() => {
      wrapper.unmount()
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('opens sign-in modal on click below header', () => {
      expect(document.querySelector('.test-signin-modal [href="/account/login"]')).toBeDefined()
    })
  })
})
