/* global describe, it, expect, jest */
import React from 'react'
import { mount } from 'enzyme'
import NumberField from './NumberField'

describe('NumberField', () => {
  const wrapper = (props) => mount(
    <NumberField
      isReadOnly={false}
      value={3}
      initialValue={5}
      placeholder={'a-placeholder'}
      onChange={jest.fn()}
      onSubmit={jest.fn()}
      onReset={jest.fn()}
      {...props}
    />
  )

  it('should call onChange but not onSubmit when text changes', () => {
    const w = wrapper()
    w.find('input').simulate('change', { target: { value: '6' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith(6)
    expect(w.prop('onSubmit')).not.toHaveBeenCalled()
  })

  it('should not show a submit button when value is unchanged', () => {
    const w = wrapper({
      value: 5,
      initialValue: 5
    })
    expect(w.find('button')).toHaveLength(0)
  })

  it('should submit a changed value by button', () => {
    const w = wrapper({
      value: 6,
      initialValue: 5
    })
    w.find('button').simulate('click')
    expect(w.prop('onSubmit')).toHaveBeenCalled()
  })

  it('should submit a changed value by pressing Enter', () => {
    const w = wrapper({
      value: 6,
      initialValue: 5
    })
    w.find('input').simulate('keydown', { keyCode: 13, preventDefault: jest.fn() })
    expect(w.prop('onSubmit')).toHaveBeenCalled()
  })

  it('should change back to initial value by pressing Escape', () => {
    const w = wrapper({
      value: 6,
      initialValue: 5
    })
    w.find('input').simulate('keydown', { keyCode: 27, preventDefault: jest.fn() })
    expect(w.prop('onReset')).toHaveBeenCalled()
  })

  it('should disable when read-only', () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('input').prop('readOnly')).toBe(true)
  })

  it('should return null when text field cleared, not 0', () => {
    const w = wrapper()
    w.find('input').simulate('change', { target: { value: '' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith(null)
  })

})
