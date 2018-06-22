import React from 'react'
import { mount } from 'enzyme'
import { DataVersionModal } from './DataVersionModal'

describe('DataVersionModal', () => {
  const Versions = [
    { id: '2000', date: new Date(234567890), isSeen: false },
    { id: '1000', date: new Date(123456789), isSeen: true },
  ]

  let _wrapper = null

  afterEach(() => {
    if (_wrapper !== null) {
      _wrapper.unmount()
      _wrapper = null
    }
  })

  const wrapper = (extraProps) => {
    return _wrapper = mount(
      <DataVersionModal
        fetchWfModuleId={123}
        fetchWfModuleName={'fetch'}
        fetchVersions={Versions}
        selectedFetchVersionId={'1000'}
        wfModuleId={124}
        notificationsEnabled={false}
        onClose={jest.fn()}
        onChangeFetchVersionId={jest.fn()}
        onChangeNotificationsEnabled={jest.fn()}
        {...extraProps}
        />
    )
  }

  it('matches snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('displays versions', () => {
    const w = wrapper()
    expect(w.find('label.seen.selected time').text()).toEqual('Jan. 2, 1970 – 5:17 a.m.')
    expect(w.find('label.unseen time').text()).toEqual('Jan. 3, 1970 – 12:09 p.m.')
  })

  it('selects a version', () => {
    const w = wrapper()

    // Click new version; verify it's clicked
    w.find('label.unseen input').simulate('change', { target: { checked: true } })
    expect(w.find('label.unseen input').prop('checked')).toBe(true)

    // Click 'Load'
    w.find('button[name="load"]').simulate('click')
    expect(w.prop('onChangeFetchVersionId')).toHaveBeenCalledWith(123, '2000')
    expect(w.prop('onClose')).toHaveBeenCalled()
  })

  it('cancels with a close button', () => {
    const w = wrapper()

    // Click new version; verify it's clicked
    w.find('label.unseen input').simulate('change', { target: { checked: true } })

    w.find('button.close').simulate('click')
    expect(w.prop('onClose')).toHaveBeenCalled()
  })

  it('enables/disables notifications', () => {
    const w = wrapper()

    w.find('input[name="notifications-enabled"]').simulate('change', { target: { checked: true } })
    expect(w.prop('onChangeNotificationsEnabled')).toHaveBeenCalledWith(124, true)
    w.setProps({ notificationsEnabled: true }) // simulate onChangeNotificationsEnabled()
    expect(w.find('input[name="notifications-enabled"]').prop('checked')).toBe(true)

    w.find('input[name="notifications-enabled"]').simulate('change', { target: { checked: false } })
    expect(w.prop('onChangeNotificationsEnabled')).toHaveBeenCalledWith(124, true)
    w.setProps({ notificationsEnabled: false }) // simulate onChangeNotificationsEnabled()
    expect(w.find('input[name="notifications-enabled"]').prop('checked')).toBe(false)
  })
})
