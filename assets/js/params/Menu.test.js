import React from 'react'
import { shallow } from 'enzyme'
import Menu from './Menu';

describe('Menu', () => {
  it('matches snapshot', () => {
    const w = shallow(
      <Menu
        items='Apple|Kittens|Banana'
        name='somename'
        value={1}
        onChange={jest.fn()}
        isReadOnly={false}
      />
    )
    expect(w).toMatchSnapshot()
  })
})
