/* globals afterEach, describe, expect, it */
import React from 'react'
import { act } from 'react-dom/test-utils'
import WfHamburgerMenu from './WfHamburgerMenu'
import { mountWithI18n } from './i18n/test-utils'

describe('WfHamburgerMenu', () => {
  let wrapper // all tests must mount one
  afterEach(() => wrapper.unmount())

  it('renders logged in, non-read only', async () => {
    wrapper = mountWithI18n(
      <WfHamburgerMenu
        workflowId={1}
        api={{}}
        isReadOnly={false}
        user={{ id: 100 }}
      />
    )

    wrapper.find('button.context-button').simulate('click')
    await act(async () => await null) // Popper update() - https://github.com/popperjs/react-popper/issues/350

    expect(wrapper).toMatchSnapshot() // one snapshot only, in most common case

    expect(wrapper.find('a[href="/workflows/"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem Trans[message="Log Out"]')).toHaveLength(1)
  })

  it('renders logged in, read only', async () => {
    wrapper = mountWithI18n(
      <WfHamburgerMenu
        workflowId={1}
        api={{}}
        isReadOnly
        user={{ id: 100 }}
      />
    )

    wrapper.find('button.context-button').simulate('click')
    await act(async () => await null) // Popper update() - https://github.com/popperjs/react-popper/issues/350

    expect(wrapper.find('a[href="/workflows/"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem Trans[message="Log Out"]')).toHaveLength(1)
  })

  it('renders logged out, read only', async () => {
    wrapper = mountWithI18n(
      <WfHamburgerMenu
        workflowId={1}
        api={{}}
        isReadOnly
        user={undefined}
      />
    )

    wrapper.find('button.context-button').simulate('click')
    await act(async () => await null) // Popper update() - https://github.com/popperjs/react-popper/issues/350

    expect(wrapper.find('a[href="//workbenchdata.com"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem[children="Log out"]')).toHaveLength(0)
  })

  it('renders without a workflowId', async () => {
    // this happens on Workflow list page
    wrapper = mountWithI18n(
      <WfHamburgerMenu
        api={{}}
        isReadOnly
        user={{ id: 100 }}
      />
    )

    wrapper.find('button.context-button').simulate('click')
    await act(async () => await null) // Popper update() - https://github.com/popperjs/react-popper/issues/350

    expect(wrapper.find('a[href="//workbenchdata.com"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem Trans[message="Log Out"]')).toHaveLength(1)
  })
})
