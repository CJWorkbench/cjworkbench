/* globals describe, it, expect */
import React from 'react'
import StepHeader from './StepHeader'
import { mount } from 'enzyme'

describe('StepHeader', () => {
  it('Mounts selected', () => {
    const wrapper = mount(
      <StepHeader
        status='busy'
        isSelected
        moduleName='Some module name'
        moduleIcon='some-icon'
      />
    )
    expect(wrapper).toMatchSnapshot()
    expect(wrapper.find('.module-name').text()).toEqual('Some module name')
    expect(wrapper.find('.module-icon').props().className).toEqual('icon-some-icon module-icon t-vl-gray mr-2')
  })

  it('Mounts unselected', () => {
    const wrapper = mount(
      <StepHeader
        status='busy'
        isSelected={false}
        moduleName='Some module name'
        moduleIcon='some-icon'
      />
    )
    expect(wrapper).toMatchSnapshot()
    expect(wrapper.find('.module-name').text()).toEqual('Some module name')
    expect(wrapper.find('.module-icon').props().className).toEqual('icon-some-icon module-icon t-vl-gray mr-2')
  })
})
