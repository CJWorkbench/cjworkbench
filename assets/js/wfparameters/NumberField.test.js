/* global describe, it, expect, jest */
import React from 'react'
import { shallow } from 'enzyme'
import NumberField from './NumberField'

describe('NumberField', () => {
  const wrapper = (props) => shallow(
    <NumberField
      isReadOnly={false}
      value={3}
      initialValue={5}
      placeholder={'a-placeholder'}
      onChange={jest.fn()}
      onSubmit={jest.fn()}
      {...props}
    />
  )

  it('should call onChange but not onSubmit when text changes', () => {
    const w = wrapper()
    w.find('input').simulate('change', { target: { value: 'new' } })
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
    w.find('input').simulate('keydown', { keyCode: 13 })
    expect(w.prop('onSubmit')).toHaveBeenCalled()
  })

  it('should change back to initial value by pressing Escape', () => {
    const w = wrapper({
      value: 'new',
      initialValue: 'old'
    })
    w.find('input').simulate('keydown', { keyCode: 27 })
    expect(w.prop('onSubmit')).not.toHaveBeenCalled()
    expect(w.prop('onChange')).toHaveBeenCalledWith('old')
  })

  it('should not allow newlines', () => {
    const w = wrapper()
    w.find('input').simulate('change', { target: { value: 'abc\ndef' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith('abcdef')
  })

  it('should disable when read-only', () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('input').prop('readonly')).toBe(true)
  })
})
