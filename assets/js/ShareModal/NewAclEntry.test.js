/* globals describe, expect, it, jest */
import React from 'react'
import { mount } from 'enzyme'
import NewAclEntry from './NewAclEntry'

describe('NewAclEntry', () => {
  const wrapper = (extraProps = {}) => mount(
    <NewAclEntry
      ownerEmail='owner@example.org'
      updateAclEntry={jest.fn()}
      {...extraProps}
    />
  )

  it('should add an email', () => {
    const w = wrapper()
    w.find('input[name="email"]').instance().value = 'a@example.com'
    w.find('form').simulate('submit')

    expect(w.prop('updateAclEntry')).toHaveBeenCalledWith('a@example.com', false)
    expect(w.find('input[name="email"]').instance().value).toEqual('')
  })

  it('should no-op on ownerEmail', () => {
    const w = wrapper({ ownerEmail: 'a@example.com' })
    w.find('input[name="email"]').instance().value = 'a@example.com'
    w.find('form').simulate('submit')

    expect(w.prop('updateAclEntry')).not.toHaveBeenCalled()
    // We still want to clear the text field, though. (The owner appears in the
    // ACL display, so the user does see email he/she entered -- just once, not
    // twice.)
    expect(w.find('input[name="email"]').instance().value).toEqual('')
  })

  // We can't really test form validation with Enzyme, because it doesn't
  // use real HTML events. Sigh.

  // it('should deny an invalid email')
})
