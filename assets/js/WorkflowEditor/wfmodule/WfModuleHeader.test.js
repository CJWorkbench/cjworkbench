/* globals describe, it, expect */
import React from 'react'
import WfModuleHeader from './WfModuleHeader'
import { mount } from 'enzyme'

describe('WfModuleHeader', () => {
  it('Mounts selected', () => {
    const wrapper = mount(
      <WfModuleHeader
        status='busy'
        isSelected
        moduleName='Some module name'
        moduleIcon='some-icon'
      />
    )
    expect(wrapper).toMatchSnapshot()
    expect(wrapper.find('.WFmodule-name').text()).toEqual('Some module name')
    expect(wrapper.find('.WFmodule-icon').props().className).toEqual('icon-some-icon WFmodule-icon t-vl-gray mr-2')
  })

  it('Mounts unselected', () => {
    const wrapper = mount(
      <WfModuleHeader
        status='busy'
        isSelected={false}
        moduleName='Some module name'
        moduleIcon='some-icon'
      />
    )
    expect(wrapper).toMatchSnapshot()
    expect(wrapper.find('.WFmodule-name').text()).toEqual('Some module name')
    expect(wrapper.find('.WFmodule-icon').props().className).toEqual('icon-some-icon WFmodule-icon t-vl-gray mr-2')
  })
})
