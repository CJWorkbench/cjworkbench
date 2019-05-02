import React from 'react'
import { shallow } from 'enzyme'
import Menu from './Menu';

describe('Menu', () => {
  it('matches snapshot', () => {
    const w = shallow(
      <Menu
        enumOptions={[{label: 'Apple', value: 'apple'}, {label: 'Kittens', value: 'kittens'}, {label: 'Banana', value: 'banana'}]}
        name='somename'
        value={'kittens'}
        onChange={jest.fn()}
        isReadOnly={false}
      />
    )
    expect(w).toMatchSnapshot()
  })
})
