/* globals describe, expect, it */
import React from 'react'
import Navbar from './Navbar'
import { shallowWithI18n } from '../test-utils'

describe('Navbar', () => {
  it('Renders correctly', () => {
    const wrapper = shallowWithI18n(<Navbar />)
    expect(wrapper).toMatchSnapshot()
  })
})
