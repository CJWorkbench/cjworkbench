import React from 'react'
import { mount } from 'enzyme'
import NewAclEntry from './NewAclEntry'

describe('NewAclEntry', () => {
  const wrapper = () => mount(
    <NewAclEntry
      onCreate={jest.fn()}
    />
  )

  it('should add an email', () => {
    const w = wrapper()
    w.find('input[name="email"]').instance().value = 'a@example.com'
    w.find('form').simulate('submit')

    expect(w.prop('onCreate')).toHaveBeenCalledWith('a@example.com', false)
    expect(w.find('input[name="email"]').instance().value).toEqual('')
  })

  // We can't really test form validation with Enzyme, because it doesn't
  // use real HTML events. Sigh.

  // it('should deny an invalid email')
})
