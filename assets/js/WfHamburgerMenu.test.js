import React from 'react'
import WfHamburgerMenu from './WfHamburgerMenu'
import { mount } from 'enzyme'

describe('WfHamburgerMenu', () => {
  let wrapper // all tests must mount one
  afterEach(() => wrapper.unmount())

  it('renders logged in, non-read only', () => {
    wrapper = mount(<WfHamburgerMenu
      workflowId={1}
      api={{}}
      isReadOnly={false}
      user={{ id: 100 }}
    />)

    wrapper.find('button.context-button').simulate('click')
    expect(wrapper).toMatchSnapshot() // one snapshot only, in most common case

    expect(wrapper.find('a[href="/workflows/"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem[children="Import Module"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem[children="Log Out"]')).toHaveLength(1)
  })

  it('renders logged in, read only', () => {
    wrapper = mount(<WfHamburgerMenu
      workflowId={1}
      api={{}}
      isReadOnly
      user={{ id: 100 }}
    />)

    wrapper.find('button.context-button').simulate('click')
    expect(wrapper.find('a[href="/workflows/"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem[children="Import Module"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem[children="Log Out"]')).toHaveLength(1)
  })

  it('renders logged out, read only', () => {
    wrapper = mount(<WfHamburgerMenu
      workflowId={1}
      api={{}}
      isReadOnly
      user={undefined}
    />)

    wrapper.find('button.context-button').simulate('click')
    expect(wrapper.find('a[href="//workbenchdata.com"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem[children="Import Module"]')).toHaveLength(0)
    expect(wrapper.find('DropdownItem[children="Log out"]')).toHaveLength(0)
  })

  it('renders without a workflowId', () => {
    // this happens on Workflow list page
    wrapper = mount(<WfHamburgerMenu
      api={{}}
      isReadOnly
      user={{ id: 100 }}
    />)

    wrapper.find('button.context-button').simulate('click')
    expect(wrapper.find('a[href="//workbenchdata.com"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem[children="Import Module"]')).toHaveLength(0)
    expect(wrapper.find('DropdownItem[children="Log Out"]')).toHaveLength(1)
  })
})
