/* globals describe, expect, it, jest */
import React from 'react'
import OAuth from './OAuth'
import { mountWithI18n } from '../../i18n/test-utils'

describe('OAuth', () => {
  const wrapper = (extraProps) => {
    return mountWithI18n(
      <OAuth
        name='x'
        startCreateSecret={jest.fn()}
        deleteSecret={jest.fn()}
        secretMetadata={{ name: 'a secret' }}
        secretLogic={{ service: 'google' }}
        isOwner
        {...extraProps}
      />
    )
  }

  it('matches snapshot', () => {
    const w = wrapper({})
    expect(w).toMatchSnapshot()
  })

  it('does not show "Sign in" link when not owner', () => {
    const w = wrapper({ secretMetadata: null, isOwner: false })
    expect(w.find('button.connect')).toHaveLength(0)
  })

  it('renders without a secret', () => {
    const w = wrapper({ secretMetadata: null })
    expect(w.find('button.connect')).toHaveLength(1)
    w.find('button.connect').simulate('click')
    expect(w.prop('startCreateSecret')).toHaveBeenCalledWith('x')
  })

  it('does not show "Sign out" link when not owner', () => {
    const w = wrapper({ isOwner: false })
    expect(w.find('button.disconnect')).toHaveLength(0)
  })

  it('disconnects', () => {
    const w = wrapper({ secretMetadata: { name: 'foo@example.org' } })
    w.find('button.disconnect').simulate('click')
    expect(w.prop('deleteSecret')).toHaveBeenCalledWith('x')
  })
})
