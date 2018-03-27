import React from 'react'
import StatusBar from './StatusBar'
import { shallow } from 'enzyme'

describe('Status bar', () => {
  it('Renders the error color', () => {
    let wrapper = shallow(
      <StatusBar
        isSelected={true}
        status="error"
      />
    );
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.find('div').first().props().className).toEqual("module-output-bar-red");
  });

  it('Renders the unselected error color', () => {
    let wrapper = shallow(
      <StatusBar
        isSelected={false}
        status="error"
      />
    );
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.find('div').first().props().className).toEqual("module-output-bar-pink");
  });

  it('Renders the busy color', () => {
    let wrapper = shallow(
      <StatusBar
        isSelected={false}
        status="busy"
      />
    );
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.find('div').first().props().className).toEqual("module-output-bar-orange");
  });

  it('Renders the selected ready color', () => {
    let wrapper = shallow(
      <StatusBar
        isSelected={true}
        status="ready"
      />
    );
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.find('div').first().props().className).toEqual("module-output-bar-blue");
  });

  it('Renders the unselected ready color', () => {
    let wrapper = shallow(
      <StatusBar
        isSelected={false}
        status="ready"
      />
    );
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.find('div').first().props().className).toEqual("module-output-bar-white");
  });

  it('Renders the default color', () => {
    let wrapper = shallow(
      <StatusBar
        isSelected={false}
        status="garbage_return_status"
      />
    );
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.find('div').first().props().className).toEqual("module-output-bar-white");
  });
});