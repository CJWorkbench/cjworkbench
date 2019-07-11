/* globals describe, expect, it, jest */
import React from 'react'
import { mount } from 'enzyme'
import AclEntry from './AclEntry'

describe('AclEntry', () => {
  // We mount() because we're testing both Role and AclEntry together.
  const wrapper = (props = {}) => mount(
    <AclEntry
      isReadOnly={false}
      email='user@example.org'
      canEdit={false}
      updateAclEntry={jest.fn()}
      deleteAclEntry={jest.fn()}
      {...props}
    />
  )

  it('should render the email and role', () => {
    const w = wrapper({ email: 'a@example.com', canEdit: true })
    expect(w.find('.email').text()).toEqual('a@example.com')
    expect(w.find('button.dropdown-toggle').text()).toEqual('Can edit')
  })

  it('should change editor to viewer', () => {
    const w = wrapper({ email: 'a@example.com', canEdit: true })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button.can-edit-false').simulate('click')
    expect(w.prop('updateAclEntry')).toHaveBeenCalledWith('a@example.com', false)
  })

  it('should change viewer to editor', () => {
    const w = wrapper({ email: 'a@example.com', canEdit: false })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button.can-edit-true').simulate('click')
    expect(w.prop('updateAclEntry')).toHaveBeenCalledWith('a@example.com', true)
  })

  it('should no-op when trying to change viewer to viewer', () => {
    const w = wrapper({ email: 'a@example.com', canEdit: false })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button.can-edit-false').simulate('click')
    expect(w.prop('updateAclEntry')).not.toHaveBeenCalled()
  })

  it('should no-op when trying to change editor to editor', () => {
    const w = wrapper({ email: 'a@example.com', canEdit: true })
    w.find('button.dropdown-toggle').simulate('click')
    w.find('button.can-edit-true').simulate('click')
    expect(w.prop('updateAclEntry')).not.toHaveBeenCalled()
  })

  it('should delete', () => {
    const w = wrapper({ email: 'a@example.com' })
    w.find('button.delete').simulate('click')
    expect(w.prop('deleteAclEntry')).toHaveBeenCalledWith('a@example.com')
  })

  it('should render read-only', () => {
    const w = wrapper({ isReadOnly: true, canEdit: true })
    expect(w.find('.role').text()).toEqual('Can edit')
    expect(w.find('button')).toHaveLength(0)
  })
})
