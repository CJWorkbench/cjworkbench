import React from 'react'
import { mount } from 'enzyme'

import Radio from './Radio'

describe('Radio', () => {
  const wrapper = (extraProps = {}) => mount(
    <Radio
      isReadOnly={false}
      name='radio'
      fieldId='radio'
      value={0}
      onChange={jest.fn()}
      {...extraProps}
    />
  )

  it('renders correctly', () => {
    const w = wrapper({ options: [ { value: 'x', label: 'X' } ] })
    expect(wrapper).toMatchSnapshot()
  })

  it('renders number of buttons correctly', () => {
    const w = wrapper({ options: [
      { value: 'x', label: 'X' },
      { value: 'y', label: 'Y' },
      { value: 'z', label: 'Z' }
    ]})
    expect(w.find('input[type="radio"]')).toHaveLength(3)
  })

  it('render and handle click of deprecated "items" (as opposed to "options")', () => {
    const w = wrapper({ items: 'first|second' })
    w.find('input[value="1"]').simulate('change', { target: { value: '1' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith(1)
  })

  it('render and handle click of non-String values', () => {
    const w = wrapper({
      options: [
        { value: 0, label: 'first' },
        { value: 1, label: 'second' }
      ]
    })
    w.find('input[value="1"]').simulate('change', { target: { value: '1' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith(1)
  })

  it('should be disabled when read only', () => {
    // HTML5 "readOnly" input is editable. Oops.
    const w = wrapper({
      isReadOnly: true,
      name: 'foo',
      options: [
        { value: 'x', label: 'off' },
        { value: 'y', label: 'on' },
      ]
    })
    expect(w.find('input[value="x"]').prop('disabled')).toBe(true)
    expect(w.find('input[value="y"]').prop('disabled')).toBe(true)
  })
})
