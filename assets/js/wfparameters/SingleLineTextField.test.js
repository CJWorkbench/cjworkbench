/* global describe, it, expect, jest */
import React from 'react'
import { mount } from 'enzyme' // mount, not shallow, because we do DOM calculations
import SingleLineTextField from './SingleLineTextField'

describe('SingleLineTextField', () => {
  const wrapper = (props) => mount(
    <SingleLineTextField
      onChange={jest.fn()}
      onSubmit={jest.fn()}
      isReadOnly={false}
      name='field-name'
      value='initialValue'
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
      initialValue: 'val'
    })
    expect(w.find('button')).toHaveLength(0)
  })

  it('should submit a changed value by button', () => {
    const w = wrapper({
      value: 'new',
      initialValue: 'old'
    })
    w.find('button').simulate('click')
    expect(w.prop('onSubmit')).toHaveBeenCalled()
  })

  it('should submit a changed value by pressing Enter', () => {
    const w = wrapper({
      value: 'new',
      initialValue: 'old'
    })
    w.find('textarea').simulate('keydown', { keyCode: 13 })
    expect(w.prop('onSubmit')).toHaveBeenCalled()
  })

  it('should change back to initial value by pressing Escape', () => {
    const w = wrapper({
      value: 'new',
      initialValue: 'old'
    })
    w.find('textarea').simulate('keydown', { keyCode: 27 })
    expect(w.prop('onSubmit')).not.toHaveBeenCalled()
    expect(w.prop('onChange')).toHaveBeenCalledWith('old')
  })

  it('should not allow newlines', () => {
    const w = wrapper()
    w.find('textarea').simulate('change', { target: { value: 'abc\ndef' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith('abcdef')
  })

  it('should disable when read-only', () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('textarea').prop('readonly')).toBe(true)
  })
})
