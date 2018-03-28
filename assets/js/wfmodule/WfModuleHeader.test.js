import React from 'react'
import WfModuleHeader from './WfModuleHeader'
import { mount } from 'enzyme'

describe('WfModuleHeader', () => {
  it('Mounts and focuses', () => {
    let wrapper = mount(
      <WfModuleHeader
        status="busy"
        isSelected={true}
        moduleName="Some module name"
        moduleIcon="some-icon"
        focusModule={jest.fn()}
      />
    );
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.props().focusModule.mock.calls.length).toEqual(1);
    expect(wrapper.find('.WFmodule-name').text()).toEqual("Some module name");
    expect(wrapper.find('.WFmodule-icon').props().className).toEqual('icon-some-icon WFmodule-icon t-vl-gray mr-2');
  });

  it('Mounts and does not focus', () => {
    let wrapper = mount(
      <WfModuleHeader
        status="busy"
        isSelected={false}
        moduleName="Some module name"
        moduleIcon="some-icon"
        focusModule={jest.fn()}
      />
    );
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.props().focusModule.mock.calls.length).toEqual(0);
    expect(wrapper.find('.WFmodule-name').text()).toEqual("Some module name");
    expect(wrapper.find('.WFmodule-icon').props().className).toEqual('icon-some-icon WFmodule-icon t-vl-gray mr-2');
  });
});
