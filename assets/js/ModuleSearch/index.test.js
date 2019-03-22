/**
 * Testing Stories:
 * -Renders a search bar
 * -Search bar will render suggestions of modules matching input
 * 
 */
jest.mock('../lessons/lessonSelector', () => jest.fn()) // same mock in every test :( ... we'll live

// https://github.com/FezVrasta/popper.js#how-to-use-popperjs-in-jest
jest.mock('popper.js', () => {
  const PopperJS = jest.requireActual('popper.js')

  return class {
    static placements = PopperJS.placements

    constructor() {
      return {
        destroy: () => {},
        scheduleUpdate: () => {}
      }
    }
  }
})


import React from 'react'
import ConnectedModuleSearch, { ModuleSearch } from './index'
import { mount, shallow } from 'enzyme'
import { createStore } from 'redux'
import { Provider } from 'react-redux'
import lessonSelector from '../lessons/lessonSelector'

describe('ModuleSearch', () => {
  const modules = {
    'enigma': {
      idName: 'enigma',
      name: "Load from Enigma",
      description: 'Enigma description',
      category: "Add data",
      icon: "url",
      isLessonHighlight: true,
    },
    'filter': {
      idName: 'filter',
      name: "Filter by Text",
      description: 'Text description',
      category: "Filter",
      icon: "filter",
      isLessonHighlight: false,
    }
  }
  const modulesArray = Object.keys(modules).map(id => modules[id])

  let defaultProps
  beforeEach(() => defaultProps = {
    onClickModule: jest.fn(),
    onCancel: jest.fn(),
    index: 2,
    modules: modulesArray,
    isLessonHighlight: false,
  })

  describe('most tests', () => {
    let wrapper
    beforeEach(() => wrapper = mount(<ModuleSearch {...defaultProps}/>))
    afterEach(() => wrapper.unmount())

    let searchField
    beforeEach(() => searchField = wrapper.find('input[name="moduleQ"]'))

    it('matches snapshot', () => { 
      expect(wrapper).toMatchSnapshot()
    })

    it('finds all suggestions by default', () => {
      expect(wrapper.text()).toMatch(/Load from Enigma/)
      expect(wrapper.text()).toMatch(/Filter by Text/)
    })

    it('finds a suggestion matching search input', () => { 
      searchField.simulate('change', {target: {value: 'a'}})
      wrapper.update()
      expect(wrapper.text()).toMatch(/Load from Enigma/)
      expect(wrapper.text()).not.toMatch(/Filter by Text/)

      // Search in description
      searchField.simulate('change', {target: {value: 'description'}})
      wrapper.update()
      expect(wrapper.text()).toMatch(/Load from Enigma/)
      expect(wrapper.text()).toMatch(/Filter by Text/)
    })

    it('calls onCancel on form reset (e.g., clicking button.close)', () => { 
      // search field should be empty at start
      wrapper.find('form').simulate('reset')
      expect(wrapper.prop('onCancel')).toHaveBeenCalled()
    })

    it('calls onCancel on pressing Escape', () => {
      searchField.simulate('keyDown', { keyCode: 27 })
      expect(wrapper.prop('onCancel')).toHaveBeenCalled()
    })

    it('calls onClickModule on click', () => {
      wrapper.find('li[data-module-name="Load from Enigma"]').simulate('click')
      expect(wrapper.prop('onClickModule')).toHaveBeenCalledWith('enigma')
    })

    it('should lesson-highlight module', () => {
      expect(wrapper.find('li[data-module-name="Load from Enigma"]').hasClass('lesson-highlight')).toBe(true)
      expect(wrapper.find('li[data-module-name="Filter by Text"]').hasClass('lesson-highlight')).toBe(false)
    })

    it('should sort modules in alphabetical order', () => {
      wrapper.unmount()
      const modules = {
        'a': {
          idName: 'a',
          name: "Z",
          description: 'desc',
          category: "Add data",
          icon: "url",
          isLessonHighlight: false
        },
        'b': {
          idName: 'b',
          name: "Y",
          description: 'desc',
          category: "Filter",
          icon: "filter",
          isLessonHighlight: false
        },
        'c': {
          idName: 'c',
          name: "H",
          description: 'desc',
          category: "Filter",
          icon: "filter",
          isLessonHighlight: false,
        },
        'd': {
          idName: 'd',
          name: "A",
          description: 'desc',
          category: "Add data",
          icon: "filter",
          isLessonHighlight: false,
        }
      }
      const modulesArray = Object.keys(modules).map(id => modules[id])

      let defaultProps = {
        onClickModule: jest.fn(),
        onCancel: jest.fn(),
        index: 2,
        modules: modulesArray,
        isLessonHighlight: false
      }

      wrapper = mount(<ModuleSearch {...defaultProps}/>)

      let resultList = wrapper.prop('modules').map(x => x.name)
      let expectedResult = ['A', 'H', 'Y', 'Z']
      expect(resultList).toEqual(expectedResult)
    })

    it('should show a popover when hovering on a module', () => {
      expect(wrapper.find('SearchResultDescription')).toHaveLength(0)
      wrapper.find('li[data-module-name="Filter by Text"]').simulate('mouseEnter')
      wrapper.update()
      expect(wrapper.find('SearchResultDescription')).toHaveLength(1)
    })
  })
    
  it('should highlight search box based on isLessonHighlight', () => {
    const noHighlight = shallow(<ModuleSearch {...defaultProps} isLessonHighlight={false} />)
    expect(noHighlight.hasClass('lesson-highlight')).toBe(false)

    const yesHighlight = shallow(<ModuleSearch {...defaultProps} isLessonHighlight={true} />)
    expect(yesHighlight.hasClass('lesson-highlight')).toBe(true)
  })

  describe('with store', () => {
    let store
    let wrapper
    let nonce = 0

    function highlight(index, moduleName) {
      lessonSelector.mockReturnValue({
        testHighlight: test => {
          if (index === null) return false
          return test.type === 'Module' && (test.name ? (test.name === moduleName) : true) && test.index === index
        }
      })

      // trigger a change
      store.dispatch({ type: 'whatever', payload: ++nonce })
    }

    beforeEach(() => {
      lessonSelector.mockReset()

      // Store just needs to change, to trigger mapStateToProps. We don't care
      // about its value
      store = createStore((_, action) => ({ modules, ...action.payload }), { modules })

      highlight(null)

      wrapper = mount(
        <Provider store={store}>
          <ConnectedModuleSearch {...defaultProps} alwaysRenderSuggestions={true} />
        </Provider>
      )
    })
    afterEach(() => {
      wrapper.unmount()
    })

    it('loads modules', () => {
      expect(wrapper.text()).toMatch(/Load from Enigma/)
    })

    it('highlights the search box', () => {
      highlight(2, null)
      wrapper.update()
      expect(wrapper.find('.module-search').prop('className')).toMatch(/\blesson-highlight\b/)

      highlight(1, null)
      wrapper.update()
      expect(wrapper.find('.module-search').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })
  })
})
