/* globals beforeEach, describe, expect, it, jest */
import { createRef } from 'react'
import EditableNotes from './EditableNotes'
import { shallow, mount } from 'enzyme'

describe('EditableNotes', () => {
  let wrapper

  // Can't test "startsFocused" with shallow(), because there's no DOM element to focus

  describe('read-only', () => {
    beforeEach(() => {
      wrapper = shallow(
        <EditableNotes
          isReadOnly
          placeholder='placeholder'
          value='This is the best module'
          inputRef={createRef()}
          onChange={jest.fn()}
          onBlur={jest.fn()}
          onCancel={jest.fn()}
        />
      )
      return wrapper
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('renders plain note', () => {
      expect(wrapper.find('div.editable-notes-read-only').text()).toEqual(
        'This is the best module'
      )
    })
  })

  describe('editable', () => {
    let props

    beforeEach(() => {
      props = {
        isReadOnly: false,
        placeholder: 'placeholder',
        value: 'This is the best module',
        inputRef: createRef(),
        onChange: jest.fn(),
        onBlur: jest.fn(),
        onCancel: jest.fn()
      }

      wrapper = mount(<EditableNotes {...props} />)
    })

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })

    it('renders note in edit state', () => {
      expect(wrapper.find('textarea').prop('value')).toEqual(
        'This is the best module'
      )
    })

    it('lets user enter and save a note', () => {
      const textarea = wrapper.find('textarea')
      textarea.simulate('change', {
        target: { value: 'This is a mediocre module' }
      })
      textarea.simulate('blur')
      expect(props.onChange).toHaveBeenCalled()
      expect(props.onChange.mock.calls[0][0].target.value).toEqual(
        'This is a mediocre module'
      )
      expect(props.onBlur).toHaveBeenCalled()
    })

    it('sets inputRef to be a textarea', () => {
      const textarea = wrapper.find('textarea').getDOMNode()
      expect(props.inputRef.current).toBe(textarea)
    })

    it('exits if user presses Escape', () => {
      const textarea = wrapper.find('textarea')
      textarea.simulate('keydown', {
        target: textarea.getDOMNode(),
        key: 'Escape'
      })
      expect(props.onCancel).toHaveBeenCalled()
      expect(props.onBlur).not.toHaveBeenCalled()
    })
  })
})
