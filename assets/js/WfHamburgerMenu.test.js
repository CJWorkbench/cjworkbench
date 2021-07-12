/* globals afterEach, describe, expect, it */
import { act } from 'react-dom/test-utils'
import WfHamburgerMenu from './WfHamburgerMenu'
import { mountWithI18n } from './i18n/test-utils'

describe('WfHamburgerMenu', () => {
  let wrapper // all tests must mount one
  afterEach(() => wrapper.unmount())

  it('renders', async () => {
    wrapper = mountWithI18n(
      <WfHamburgerMenu api={{}} user={{ id: 100 }} />
    )

    wrapper.find('button.context-button').simulate('click')
    await act(async () => await null) // Popper update() - https://github.com/popperjs/react-popper/issues/350

    expect(wrapper).toMatchSnapshot() // one snapshot only, in most common case

    expect(wrapper.find('a[href="/workflows/"]')).toHaveLength(1)
    expect(wrapper.find('DropdownItem Trans[message="Log Out"]')).toHaveLength(
      1
    )
  })
})
