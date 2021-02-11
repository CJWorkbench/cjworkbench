/* global describe, it, expect, jest */
import { mount } from 'enzyme'
import Number from './Number'

describe('Number', () => {
  const wrapper = props =>
    mount(
      <Number
        isReadOnly={false}
        value={3}
        upstreamValue={5}
        name='name'
        label='Label'
        fieldId='field-id'
        placeholder='a-placeholder'
        onChange={jest.fn()}
        {...props}
      />
    )

  it('should call onChange when text changes', () => {
    const w = wrapper()
    w.find('input').simulate('change', { target: { value: '6' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith(6)
  })

  it('should change back to initial value by pressing Escape', () => {
    const w = wrapper({
      value: 6,
      upstreamValue: 5
    })
    w.find('input').simulate('keydown', {
      key: 'Escape',
      preventDefault: jest.fn()
    })
    expect(w.prop('onChange')).toHaveBeenCalledWith(5)
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
