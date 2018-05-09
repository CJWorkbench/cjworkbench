import React from 'react'
import WfHamburgerMenu  from './WfHamburgerMenu'
import { mount } from 'enzyme'


describe('WfHamburgerMenu', () => {
  let wrapper // all tests must mount one
  afterEach(() => wrapper.unmount())

  it('renders correctly', () => {
    wrapper = mount(<WfHamburgerMenu workflowId={1}/>);
    expect(wrapper).toMatchSnapshot();
  })

  it('renders correctly for workflows list page', () => {
    wrapper = mount(<WfHamburgerMenu />);
    expect(wrapper).toMatchSnapshot();
  })
})
