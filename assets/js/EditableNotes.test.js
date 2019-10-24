/* globals beforeEach, describe, expect, it, jest */
import React from 'react'
import EditableNotes from './EditableNotes'
import { shallowWithI18n } from './i18n/test-utils'

describe('EditableNotes', () => {
  let wrapper

  // Can't test "startsFocused" with shallow(), because there's no DOM element to focus

  describe('read-only', () => {
    beforeEach(() => {
      wrapper = shallowWithI18n(
        <EditableNotes
          isReadOnly
          placeholder='placeholder'
          value='This is the best module'
          onCancel={jest.fn()}
        />
      )
      return wrapper
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('renders plain note', () => {
      expect(wrapper.find('div.editable-notes-read-only').text()).toEqual('This is the best module')
    })
  })

  describe('editable', () => {
    let inputRef

    beforeEach(() => {
      inputRef = React.createRef()

      wrapper = shallowWithI18n(
        <EditableNotes
          isReadOnly={false}
          placeholder='placeholder'
          value='This is the best module'
          inputRef={inputRef}
          onChange={jest.fn()}
          onBlur={jest.fn()}
          onCancel={jest.fn()}
        />
      )
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('renders note in edit state', () => {
      expect(wrapper.find('TextareaAutosize').prop('value')).toEqual('This is the best module')
    })

    it('lets user enter and save a note', () => {
      wrapper.find('TextareaAutosize').simulate('change', { target: { value: 'This is a mediocre module' } })
      wrapper.find('TextareaAutosize').simulate('blur')
      expect(wrapper.prop('onChange')).toHaveBeenCalledWith({ target: { value: 'This is a mediocre module' } })
      expect(wrapper.prop('onBlur')).toHaveBeenCalled()
    })

    it('exits if user presses Escape', () => {
      const tag = { tagName: 'TEXTAREA', blur: jest.fn() }
      wrapper.find('TextareaAutosize').simulate('keydown', { target: tag, key: 'Escape' })
      expect(wrapper.prop('onCancel')).toHaveBeenCalled()
      expect(tag.blur).toHaveBeenCalled()
    })
  })
})
