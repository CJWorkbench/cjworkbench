/**
 * Testing Stories:
 * -Renders a Module card, with icon received from props
 * -Draggable feature exists
 * -Read-only version will collapse parent category on click
 *
 */
jest.mock('./lessons/lessonSelector', () => jest.fn()) // same mock in every test :( ... we'll live

import React from 'react'
import ConnectedModule, { Module } from './Module'
import { mount, shallow } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'
import { Provider } from 'react-redux'
import { createStore } from 'redux'
import lessonSelector from './lessons/lessonSelector'

describe('Module', () => {
  let wrapper
  let commonProps

  beforeEach(() => {
    commonProps = {
      key: 'Sweet Module',
      name: 'Sweet Module',
      icon: 'add',
      id: 88,
      addModule: jest.fn(),
      dropModule: () => {},
      connectDragSource: jest.fn(x => x),
      connectDragPreview: jest.fn(),
      isLessonHighlight: false,
      isDragging: false,
      isReadOnly: false,
    }
  })

  describe('NOT Read-only', () => {
    beforeEach(() => {
      wrapper = shallow(<Module {...commonProps} isReadOnly={false}/>)
    })

    it('Renders snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('Renders a card, with icon received from props', () => {
      expect(wrapper.find('.icon-add')).toHaveLength(1)
    })

    it('is draggable', () => {
      // find property on the Module component that indicates drag-ability
      expect(commonProps.connectDragSource).toHaveBeenCalled()
    })

    it('adds module on click', () => {
      let card = wrapper.find('.ml-module-card')
      expect(card).toHaveLength(1)
      card.simulate('click')
      expect(commonProps.addModule).toHaveBeenCalled()
    })
  })

  describe('Read-only', () => {
    beforeEach(() => {
      wrapper = shallow(<Module {...commonProps} isReadOnly={true}/>)
    })

    it('is not draggable', () => {
      expect(commonProps.connectDragSource).not.toHaveBeenCalled()
    })
  })

  describe('with redux', () => {
    let store
    let nonce = 0

    function highlight(name) {
      lessonSelector.mockReturnValue({
        testHighlight: test => test.type === 'MlModule' && test.name === name
      })

      // trigger a change
      store.dispatch({ type: 'whatever', payload: ++nonce })
      if (wrapper !== null) wrapper.update()
    }

    beforeEach(() => {
      // Store just needs to change, to trigger mapStateToProps. We don't care
      // about its value
      store = createStore((_, action) => action.payload)

      lessonSelector.mockReset()
      wrapper = null // highlight(null) will test it
      highlight(null)

      wrapper = mount(
        <Provider store={store}>
          <DragDropContextProvider backend={HTML5Backend}>
            <ConnectedModule {...commonProps}/>
          </DragDropContextProvider>
        </Provider>
      )
    })
    afterEach(() => wrapper.unmount())

    it('should add lesson-highlight when highlighted', () => {
      expect(wrapper.find('.lesson-highlight')).toHaveLength(0)

      // Highlight something else
      highlight(null)
      expect(wrapper.find('.lesson-highlight')).toHaveLength(0)

      // Highlight some other Module
      highlight('Unsweet Module')
      expect(wrapper.find('.lesson-highlight')).toHaveLength(0)

      // Highlight this Module
      highlight('Sweet Module')
      expect(wrapper.find('.lesson-highlight')).toHaveLength(1)
    })
  })
})
