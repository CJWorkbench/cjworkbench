import React from 'react'
import { mount } from 'enzyme'

import Radio from './Radio'

describe('Radio', () => {
  const wrapper = (extraProps = {}) => mount(
    <Radio
      name='radio-buttons'
      items='Apple|Kittens|Banana'
      value={0}
      onChange={jest.fn()}
      {...extraProps}
    />
  )

  it('renders correctly', () => {
    const w = wrapper({ isReadOnly: true })
    expect(wrapper).toMatchSnapshot()
  })

  it('radio renders number of buttons correctly', () => {
    const w = wrapper({ isReadOnly: false })
    expect(w.find('input[type="radio"]')).toHaveLength(3)
  })

  it('returns correct value when clicked', () => {
    const w = wrapper({ isReadOnly: false })
    w.find('input[value="2"]').simulate('change', { target: { value: '2' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith(2)
  })

  it('should be disabled when read only', () => {
    const items = 'Apple|Kittens|Banana'.split('|')
    const w = wrapper({ isReadOnly: true })
    for (const item in items) {
      const button = w.find(`input[value="${item}"]`)
      expect(button.prop('disabled')).toEqual(true)
    }
  })
})
