/**
 * Testing Stories:
 * -Renders a search bar
 * -Search bar will render suggestions of modules matching input
 * 
 */
jest.mock('./lessons/lessonSelector', () => jest.fn()) // same mock in every test :( ... we'll live

import React from 'react'
import ConnectedModuleSearch, { ModuleSearch } from './ModuleSearch'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'
import { mount, shallow } from 'enzyme'
import { createStore } from 'redux'
import { Provider } from 'react-redux'
import lessonSelector from './lessons/lessonSelector'

describe('ModuleSearch', () => {
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
  ];
  const workflow = {
    "id":15,
    "name":"What a workflow!"
  };
  let defaultProps
  beforeEach(() => defaultProps = {
    addModule: jest.fn(),
    modules,
    workflow,
    isLessonHighlight: false,
    isLessonHighlightForModuleName: jest.fn(name => false),
  })

  describe('most tests', () => {
    let wrapper
    beforeEach(() => wrapper = mount(<ModuleSearch {...defaultProps}/>))
    afterEach(() => wrapper.unmount())

    let searchField
    beforeEach(() => searchField = wrapper.find('.react-autosuggest__input'))

    it('Renders search bar', () => { 
      expect(wrapper).toMatchSnapshot(); // 1    
    })

    it('finds a suggestion matching search input', () => { 
      // Search field is focused by default, enter value to text field
      searchField.simulate('change', {target: {value: 'a'}})
      wrapper.update()
      expect(wrapper).toMatchSnapshot()
      // check for presence of suggestion matching input
      expect(wrapper.state().suggestions.length).toEqual(1)
      expect(wrapper.state().suggestions[0].modules[0].name).toEqual("Load from Enigma");      
    })

    it('Close icon will clear text from search field', () => { 
      // search field should be empty at start
      expect(wrapper.state().value).toEqual(''); 
      // close icon whould not be rendered
      let closeIcon = wrapper.find('.icon-close-white');
      expect(closeIcon).toHaveLength(0);             
      // enter value to text field
      searchField.simulate('change', {target: {value: 'wow'}});
      wrapper.update()
      expect(wrapper.state().value).toEqual('wow'); 
      // find Close icon again, click to clear search field
      closeIcon = wrapper.find('.icon-close-white');
      expect(closeIcon).toHaveLength(1);
      closeIcon.simulate('click');
      expect(wrapper.state().value).toEqual('');              
    });
  })
    
  it('should highlight search box based on isLessonHighlight', () => {
    const noHighlight = shallow(<ModuleSearch {...defaultProps} isLessonHighlight={false} />)
    expect(noHighlight.hasClass('lesson-highlight')).toBe(false)

    const yesHighlight = shallow(<ModuleSearch {...defaultProps} isLessonHighlight={true} />)
    expect(yesHighlight.hasClass('lesson-highlight')).toBe(true)
  })

  describe('watching state', () => {
    let globalLessonSelector
    beforeEach(() => {
      globalLessonSelector = lessonSelector
    })
  })

  describe('with store', () => {
    let store
    let wrapper
    let nonce = 0

    function highlight(yesOrNo, moduleName) {
      lessonSelector.mockReturnValue({
        testHighlight: test => {
          if (!yesOrNo) return false
          if (test.type === 'ModuleSearch') return true
          return test.type === 'MlModule' && test.name === moduleName
        }
      })

      // trigger a change
      store.dispatch({ type: 'whatever', payload: ++nonce })
    }

    beforeEach(() => {
      lessonSelector.mockReset()

      // Store just needs to change, to trigger mapStateToProps. We don't care
      // about its value
      store = createStore((_, action) => action.payload)

      highlight(false)

      wrapper = mount(
        <Provider store={store}>
          <DragDropContextProvider backend={HTML5Backend}>
            <ConnectedModuleSearch {...defaultProps} alwaysRenderSuggestions={true} />
          </DragDropContextProvider>
        </Provider>
      )
    })
    afterEach(() => {
      wrapper.unmount()
    })

    it('highlights the search box', () => {
      highlight(true, null)
      wrapper.update()
      expect(wrapper.find('.module-search').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('highlights a suggestion matching search input in a lesson', () => { 
      highlight(true, 'Filter by Text')

      // Find 'Load from Enigma' and 'Filter by Text', in that order
      // 'r' matches both
      const searchField = wrapper.find('.react-autosuggest__input')
      searchField.simulate('change', {target: {value: 'r'}})

      expect(wrapper.find('.module-search-result').at(0).filter('.lesson-highlight')).toHaveLength(0)
      expect(wrapper.find('.module-search-result').at(1).filter('.lesson-highlight')).toHaveLength(1)
    })
  })
});

