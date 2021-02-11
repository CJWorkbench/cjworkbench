/* global describe, it, expect, jest */
import { mount } from 'enzyme'
import SingleLineString from './SingleLineString'

describe('SingleLineString', () => {
  const wrapper = (props) => mount(
    <SingleLineString
      onChange={jest.fn()}
      onSubmit={jest.fn()}
      isReadOnly={false}
      name='field-name'
      value='value'
      upstreamValue='upstreamValue'
      placeholder='a-placeholder'
      fieldId='field-id'
      label=''
      {...props}
    />
  )

  it('should call onChange when text changes', () => {
    const w = wrapper()
    w.find('textarea').simulate('change', { target: { value: 'new' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith('new')
  })

  it('should submit a changed value by pressing Enter', () => {
    const w = wrapper({
      value: 'new',
      upstreamValue: 'old'
    })
    w.find('textarea').simulate('keydown', { key: 'Enter', preventDefault: jest.fn() })
    expect(w.prop('onSubmit')).toHaveBeenCalled()
  })

  it('should reset by pressing Escape', () => {
    const w = wrapper({
      value: 'new',
      upstreamValue: 'old'
    })
    w.find('textarea').simulate('keydown', { key: 'Escape', preventDefault: jest.fn() })
    expect(w.prop('onChange')).toHaveBeenCalledWith('old')
  })

  it('should not allow newlines', () => {
    const w = wrapper()
    w.find('textarea').simulate('change', { target: { value: 'abc\ndef' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith('abcdef')
  })

  it('should disable when read-only', () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('textarea').prop('readOnly')).toBe(true)
  })
})
