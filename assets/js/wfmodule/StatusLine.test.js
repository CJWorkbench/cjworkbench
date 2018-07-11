/* globals describe, it, expect */
import React from 'react'
import StatusLine from './StatusLine'
import { shallow } from 'enzyme'

describe('Status line', () => {
  it('Renders an error message', () => {
    let wrapper = shallow(
      <StatusLine
        status='error'
        error_msg="There's an error"
      />
    )
    expect(wrapper).toMatchSnapshot()
    expect(wrapper.find('div').first().text()).toEqual("There's an error")
  })

  it('Renders nothing for other statuses', () => {
    let wrapper = shallow(
      <StatusLine
        status='ready'
        error_msg='This should never happen'
      />
    )
    expect(wrapper.find('div').length).toEqual(0)
  })
})
