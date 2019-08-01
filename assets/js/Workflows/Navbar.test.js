/* globals describe, expect, it */
import React from 'react'
import Navbar from './Navbar'
import { shallowWithIntl as shallow } from '../test-utils'

describe('Navbar', () => {
  it('Renders correctly', () => {
    const wrapper = shallow(<Navbar />)
    expect(wrapper).toMatchSnapshot()
  })
})
