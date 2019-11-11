/* globals describe, expect, it, jest */
import React from 'react'
import ConnectedPopup, { Popup } from './Popup'
import { Provider } from 'react-redux'
import { mockStore } from '../../test-utils'
import { generateSlug } from '../../utils'
import { mountWithI18n } from '../../i18n/test-utils'

jest.mock('../../utils')

describe('ModuleSearch Popup', () => {
  const ModuleDefaults = {
    idName: 'default',
    name: 'Default',
    description: 'Default',
    category: 'Add data',
    uses_data: true,
    icon: 'url',
    isLessonHighlight: false
  }

  const modules = {
    enigma: {
      idName: 'enigma',
      name: 'Load from Enigma',
      description: 'Enigma description',
      category: 'Add data',
      uses_data: true,
      icon: 'url',
      isLessonHighlight: true
    },
    filter: {
      idName: 'filter',
      name: 'Filter by Text',
      description: 'Text description',
      category: 'Filter',
      uses_data: true,
      icon: 'filter',
      isLessonHighlight: false
    }
  }
  const modulesArray = [modules.enigma, modules.filter]

  const wrapper = (extraProps = {}) => mountWithI18n(
    <Popup
      tabSlug='tab-1'
      index={2}
      isLessonHighlight={false}
      modules={modulesArray}
      onClose={jest.fn()}
      addModule={jest.fn()}
      onUpdate={jest.fn()}
      {...extraProps}
    />
  )

  it('matches snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('finds all suggestions by default', () => {
    const w = wrapper()
    expect(w.text()).toMatch(/Load from Enigma/)
    expect(w.text()).toMatch(/Filter by Text/)
  })

  it('searches by module name', () => {
    const w = wrapper()

    w.find('input[type="search"]').simulate('change', { target: { value: 'a' } })
    expect(w.text()).toMatch(/Load from Enigma/)
    expect(w.text()).not.toMatch(/Filter by Text/)
  })

  it('searches by module description', () => {
    const w = wrapper()
    w.find('input[type="search"]').simulate('change', { target: { value: 'description' } })
    expect(w.text()).toMatch(/Load from Enigma/)
    expect(w.text()).toMatch(/Filter by Text/)
  })

  it('schedules Popper resize when search results change', () => {
    const w = wrapper()
    w.find('input[type="search"]').simulate('change', { target: { value: 'description' } })
    expect(w.prop('onUpdate')).toHaveBeenCalled()
  })

  it('calls onClose on form reset (e.g., clicking button.close)', () => {
    // search field should be empty at start
    const w = wrapper()
    w.find('form').simulate('reset')
    expect(w.prop('onClose')).toHaveBeenCalled()
    expect(w.prop('addModule')).not.toHaveBeenCalled()
  })

  it('calls onCancel on pressing Escape', () => {
    const w = wrapper()
    w.find('input[type="search"]').simulate('keyDown', { keyCode: 27 })
    expect(w.prop('onClose')).toHaveBeenCalled()
    expect(w.prop('addModule')).not.toHaveBeenCalled()
  })

  it('calls addModule and closes on click', () => {
    const w = wrapper()
    w.find('button[data-module-slug="enigma"]').simulate('click')
    expect(w.prop('addModule')).toHaveBeenCalledWith('tab-1', 2, 'enigma')
    expect(w.prop('onClose')).toHaveBeenCalled()
  })

  it('should sort modules by name', () => {
    const w = wrapper({
      modules: [
        { ...ModuleDefaults, idName: 'a', name: 'Z' },
        { ...ModuleDefaults, idName: 'b', name: 'X' },
        { ...ModuleDefaults, idName: 'c', name: 'Y' }
      ]
    })
    expect(w.text()).toMatch(/X.*Y.*Z/)
  })

  it('should show a popover description on hover', () => {
    const w = wrapper()
    w.find('button[data-module-name="Load from Enigma"]').simulate('mouseEnter')
    expect(w.find('SearchResultDescription')).toHaveLength(1)
  })

  it('should highlight search box based on isLessonHighlight', () => {
    const w = wrapper({ isLessonHighlight: true })
    expect(w.find('.module-search-popup.lesson-highlight')).toHaveLength(1)

    const w2 = wrapper({ isLessonHighlight: false })
    expect(w2.find('.module-search-popup.lesson-highlight')).toHaveLength(0)
  })

  it('should highlight lesson-suggested module', () => {
    const w = wrapper()
    expect(w.find('button[data-module-slug="enigma"]').hasClass('lesson-highlight')).toBe(true)
    expect(w.find('button[data-module-slug="filter"]').hasClass('lesson-highlight')).toBe(false)
  })

  describe('connected component', () => {
    const wrapper = (store, extraProps = {}) => mountWithI18n(
      <Provider store={store}>
        <ConnectedPopup
          tabSlug='tab-1'
          index={2}
          onClose={jest.fn()}
          isLastAddButton={false}
          {...extraProps}
        />
      </Provider>
    )

    it('gets modules from the store', () => {
      const store = mockStore({
        modules: {
          a: { id_name: 'a', name: 'AAA', category: 'Analyze', uses_data: true, description: 'A A', icon: 'a' },
          b: { id_name: 'b', name: 'BBB', category: 'Analyze', uses_data: true, description: 'B B', icon: 'b' }
        }
      })
      const w = wrapper(store)
      expect(w.text()).toMatch(/AAA.*BBB/)
    })

    it('hides !uses_data modules', () => {
      const store = mockStore({
        modules: {
          a: { id_name: 'a', name: 'AAA', category: 'Analyze', uses_data: false, description: 'A A', icon: 'a' },
          b: { id_name: 'b', name: 'BBB', category: 'Analyze', uses_data: true, description: 'B B', icon: 'b' }
        }
      })
      const w = wrapper(store)
      expect(w.text()).not.toMatch(/AAA/)
      expect(w.text()).toMatch(/BBB/)
    })

    it('hides deprecated modules', () => {
      const store = mockStore({
        modules: {
          a: { id_name: 'a', name: 'AAA', category: 'Analyze', uses_data: true, description: 'A A', icon: 'a' },
          b: {
            id_name: 'b',
            name: 'BBB',
            category: 'Analyze',
            uses_data: true,
            description: 'B B',
            icon: 'b',
            deprecated: { end_date: '2001-01-01', message: 'Please disappear' }
          }
        }
      })
      const w = wrapper(store)
      expect(w.text()).toMatch(/AAA/)
      expect(w.text()).not.toMatch(/BBB/)
    })

    it('dispatches addModule', () => {
      const api = { addModule: jest.fn(() => new Promise(() => {})) } // never resolves
      generateSlug.mockImplementation(prefix => prefix + 'X')
      const store = mockStore({
        tabs: {
          'tab-1': {
            wf_module_ids: [1, 2]
          }
        },
        wfModules: {
          1: {},
          2: {}
        },
        modules: {
          a: { id_name: 'a', name: 'AAA', category: 'Analyze', uses_data: true, description: 'A A', icon: 'a' },
          b: { id_name: 'b', name: 'BBB', category: 'Analyze', uses_data: true, description: 'B B', icon: 'b' }
        }
      }, api)
      const onClose = jest.fn()
      const w = wrapper(store, { tabSlug: 'tab-1', index: 2, onClose })
      w.find('button[data-module-slug="a"]').simulate('click')
      expect(api.addModule).toHaveBeenCalledWith('tab-1', 'step-X', 'a', 2, {})
      expect(onClose).toHaveBeenCalled()
    })

    describe('in a typical lesson', () => {
      const store = mockStore({
        lessonData: {
          sections: [
            {
              steps: [
                {
                  highlight: [{ type: 'Module', name: 'AAA', index: 0 }],
                  testJs: 'return false'
                }
              ]
            }
          ]
        },
        workflow: {
          tab_slugs: ['tab-1'],
          selected_tab_position: 0
        },
        tabs: {
          'tab-1': { wf_module_ids: [] }
        },
        modules: {
          a: { id_name: 'a', name: 'AAA', category: 'Analyze', uses_data: true, description: 'A A', icon: 'a' },
          b: { id_name: 'b', name: 'BBB', category: 'Analyze', uses_data: true, description: 'B B', icon: 'b' }
        }
      })

      it('lesson-highlights the desired module', () => {
        const w = wrapper(store, { index: 0 })
        expect(w.find('.module-search-result[data-module-slug="a"].lesson-highlight').text()).toEqual('AAA')
      })

      it('lesson-highlights the entire component', () => {
        const w = wrapper(store, { index: 0 })
        expect(w.find('.module-search-popup.lesson-highlight')).toHaveLength(1)
      })

      it('does not lesson-highlight at the wrong index', () => {
        const w = wrapper(store, { index: 2 })
        expect(w.find('.module-search-result.lesson-highlight')).toHaveLength(0)
        expect(w.find('.module-search-popup.lesson-highlight')).toHaveLength(0)
      })
    })
  })
})
