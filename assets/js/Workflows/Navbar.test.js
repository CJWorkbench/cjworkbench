import React from 'react'
import Navbar from './Navbar'
import { shallow } from 'enzyme'

describe('Navbar', () => {
  it('Renders correctly', () => {
    const wrapper = shallow(<Navbar />)
    expect(wrapper).toMatchSnapshot()
  })
})
