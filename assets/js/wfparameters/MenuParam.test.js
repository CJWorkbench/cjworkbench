import React from 'react'
import { shallow, render, mount } from 'enzyme'

import MenuParam from './MenuParam';

describe('MenuParam', () => {
  it('matches snapshot', () => {
    const w = shallow(
      <MenuParam
        items='Apple|Kittens|Banana'
        name='somename'
        selectedIdx={1}
        onChange={jest.fn()}
        isReadOnly={false}
      />
    )
    expect(w).toMatchSnapshot()
  })
})
