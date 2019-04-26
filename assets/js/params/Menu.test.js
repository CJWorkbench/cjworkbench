import React from 'react'
import { shallow } from 'enzyme'
import Menu from './Menu';

describe('Menu', () => {
  it('matches snapshot', () => {
    const w = shallow(
      <Menu
        enumOptions={[{label: 'Apple', value: 0}, {label: 'Kittens', value: 1}, {label: 'Banana', value: 2}]}
        name='somename'
        value={1}
        onChange={jest.fn()}
        isReadOnly={false}
      />
    )
    expect(w).toMatchSnapshot()
  })

  it('can choose non-String values', () => {
    const w = shallow(
      <Menu
        enumOptions={[{label: 'Apple', value: 0}, {label: 'Kittens', value: 1}, {label: 'Banana', value: 2}]}
        name='somename'
        value={1}
        onChange={jest.fn()}
        isReadOnly={false}
      />
    )
    w.find('select').simulate('change', { target: { value: w.find('option').at(0).prop('value') } })
    expect(w.instance().props.onChange).toHaveBeenCalledWith(0)
  })
})
