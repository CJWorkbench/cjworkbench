/**
 * Testing Stories:
 * -Renders a Module card, with icon received from props
 * -Draggable feature exists
 * -Read-only version will collapse parent category on click
 *
 */

import React from 'react'
import ConnectedModule, { Module } from './Module'
import { mount, shallow } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'
import { Provider } from 'react-redux'
import { createStore } from 'redux'

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

    function highlight(v) {
      store.dispatch({ type: 'x', payload: v })
    }

    beforeEach(() => {
      store = createStore(
        // reducer makes every action reset state.lesson_highlight
        (_, action) => ({ lesson_highlight: action.payload }),
        { lesson_highlight: [] }
      )

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
      highlight([ { type: 'ModuleSearch' } ])
      wrapper.update()
      expect(wrapper.find('.lesson-highlight')).toHaveLength(0)

      // Highlight some other Module
      highlight([ { type: 'MlModule', name: 'Unsweet Module' } ])
      wrapper.update()
      expect(wrapper.find('.lesson-highlight')).toHaveLength(0)

      // Highlight this Module
      highlight([ { type: 'MlModule', name: 'Sweet Module' } ])
      wrapper.update()
      expect(wrapper.find('.lesson-highlight')).toHaveLength(1)
    })
  })
})
