/**
 * Testing Stories:
 * -Renders a Module card, with icon received from props
 * -Draggable feature exists
 * -Read-only version will collapse parent category on click
 *
 */

import React from 'react'
import { Module } from './Module'
import { shallow } from 'enzyme'

describe('Module', () => {
  let wrapper
  let setOpenCategory
  let connectDragSource
  let addModule

  beforeEach(() => {
    setOpenCategory = jest.fn()
    addModule = jest.fn()
    connectDragSource = jest.fn(x => x)
  })

  describe('NOT Read-only', () => {
    beforeEach(() => {
      wrapper = shallow(
        <Module
          key={"Sweet Module"}
          name={"Sweet Module"}
          icon={"add"}
          id={88}
          addModule={addModule}
          dropModule={() => {}}
          isReadOnly={false}
          setOpenCategory={setOpenCategory}
          connectDragSource={connectDragSource}
          connectDragPreview={jest.fn()}
          isDragging={false}
          isLessonHighlight={false}
          libraryOpen={true}
        />
      )
    })

    it('Renders snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('Renders a card, with icon received from props', () => {
      expect(wrapper.find('.icon-add')).toHaveLength(1)
    })

    it('is draggable', () => {
      // find property on the Module component that indicates drag-ability
      expect(connectDragSource).toHaveBeenCalled()
    })

    it('adds module on click', () => {
      let card = wrapper.find('.ml-module-card')
      expect(card).toHaveLength(1)
      card.simulate('click')
      expect(addModule.mock.calls.length).toBe(1)
    })
  })

  describe('Read-only', () => {
    beforeEach(() => {
      wrapper = shallow(
        <Module
          key={"Sweet Module"}
          name={"Sweet Module"}
          icon={"add"}
          id={88}
          addModule={addModule}
          dropModule={() => {}}
          isReadOnly={true}
          isLessonHighlight={false}
          setOpenCategory={setOpenCategory}
          connectDragSource={connectDragSource}
          connectDragPreview={jest.fn()}
          isDragging={false}
          libraryOpen={false}
        />
      )
    })

    it('is not draggable', () => {
      expect(connectDragSource).not.toHaveBeenCalled()
    })

    it('collapses category on click', () => {
      let card = wrapper.find('.ml-module-card')
      expect(card).toHaveLength(1)
      card.simulate('click')
      expect(setOpenCategory.mock.calls.length).toBe(1)
    })
  })
})
