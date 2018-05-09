import React from 'react'
import { shallow } from 'enzyme'
import EditableNotes from './EditableNotes'
import { okResponseMock } from './utils'


describe('EditableNotes', () => {
  let wrapper

  let api
  beforeEach(() => {
    api = {
      setWfModuleNotes: okResponseMock(),
    }
  })

  // Can't test "startsFocused" with shallow(), because there's no DOM element to focus

  describe('Read-only', () => {
    beforeEach(() => wrapper = shallow(
      <EditableNotes
        value={'This is the best module'}
        wfModuleId={808}
        api={{}}
        isReadOnly={true}
        hideNotes={ () => {} }
        startFocused={false}
      />
    ))

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })
  
    it('renders plain note', () => {
      expect(wrapper.find('div.editable-notes-field').text()).toEqual('This is the best module')
    })
  })

  describe('NOT Read-only', () => {
    beforeEach(() => wrapper = shallow(
      <EditableNotes
        value={'This is the best module'}
        wfModuleId={808}
        api={api}
        isReadOnly={false}
        hideNotes={ () => {} }
        startFocused={true}
      />
    ))

    it('matches snapshot', () => {
      expect(wrapper).toMatchSnapshot()
    })
  
    it('renders note in edit state at start', () => {
      expect(wrapper.find('TextareaAutosize').prop('value')).toEqual('This is the best module')
    })

    it('lets user enter and save a note', () => {
      expect(wrapper.state().value).toEqual('This is the best module')
      wrapper.find('TextareaAutosize').prop('onChange')({ target: { value: 'This is a mediocre module' } })
      wrapper.find('TextareaAutosize').prop('onBlur')() // trigger save
      // Check that the API was called
      expect(api.setWfModuleNotes).toHaveBeenCalledWith(808, 'This is a mediocre module')
      expect(wrapper.state().value).toEqual('This is a mediocre module')
    })

    it('saves default text and closes if user enters blank note', () => {
      wrapper.find('TextareaAutosize').prop('onChange')({ target: { value: '' }})
      wrapper.find('TextareaAutosize').prop('onBlur')() // trigger save
      expect(api.setWfModuleNotes).toHaveBeenCalledWith(808, 'Write notes here')
    })
  })
})
