/* global describe, it, expect, jest */
import React from 'react'
import { mount } from 'enzyme' // mount, not shallow, because we do DOM calculations
import MultiLineString from './MultiLineString'

describe('MultiLineString', () => {
  const wrapper = (props) => mount(
    <MultiLineString
      onChange={jest.fn()}
      onSubmit={jest.fn()}
      isReadOnly={false}
      name='field-name'
      value='a,b,c\n,1,2,3'
      placeholder='a-placeholder'
      {...props}
    />
  )

  it('should call onChange but not onSubmit when text changes', () => {
    const w = wrapper()
    w.find('textarea').simulate('change', { target: { value: 'new' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith('new')
    expect(w.prop('onSubmit')).not.toHaveBeenCalled()
  })

  it('should not show a submit button when value is unchanged', () => {
    const w = wrapper({
      value: 'val',
      upstreamValue: 'val'
    })
    expect(w.find('button')).toHaveLength(0)
  })

  it('should submit a changed value by button', () => {
    const w = wrapper({
      value: 'new',
      upstreamValue: 'old'
    })
    w.find('button').simulate('click')
    expect(w.prop('onSubmit')).toHaveBeenCalled()
  })

  it('should invoke onChange when clicked out of text box', () => {
    const w = wrapper({
      value: 'new',
      upstreamValue: 'old'
    })
    w.find('textarea').simulate('blur')
    expect(w.prop('onChange')).toHaveBeenCalled()
  })

  it('should disable when read-only', () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('textarea').prop('readOnly')).toBe(true)
  })
})
