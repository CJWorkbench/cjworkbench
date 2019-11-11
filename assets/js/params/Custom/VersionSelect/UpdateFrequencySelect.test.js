/* globals afterEach, beforeEach, describe, expect, it, jest */
import { mockStore } from '../../../test-utils'
import React from 'react'
import ConnectedUpdateFrequencySelect, { UpdateFrequencySelect } from './UpdateFrequencySelect'
import { mountWithI18n } from '../../../i18n/test-utils'
import { Provider } from 'react-redux'

describe('UpdateFrequencySelect', () => {
  describe('shallow', () => {
    const defaultProps = {
      workflowId: 123,
      wfModuleId: 212,
      isReadOnly: false,
      isAnonymous: false,
      lastCheckDate: new Date(Date.parse('2018-05-28T19:00:54.154Z')),
      isAutofetch: false, // start in Manual mode
      isEmailUpdates: false,
      fetchInterval: 300,
      setEmailUpdates: jest.fn(),
      trySetAutofetch: jest.fn()
    }

    let dateSpy
    beforeEach(() => {
      dateSpy = jest.spyOn(Date, 'now').mockImplementation(() => 1527534812631)
    })
    afterEach(() => dateSpy.mockRestore())

    const wrapper = (extraProps) => {
      return mountWithI18n(
        <UpdateFrequencySelect
          {...defaultProps}
          {...extraProps}
        />
      )
    }

    it('matches snapshot', () => {
      expect(wrapper()).toMatchSnapshot()
    })

    it('does not render modal on first load', () => {
      expect(wrapper().find('UpdateFrequencySelectModal')).toHaveLength(0)
    })

    it('does not open modal when not read-only', () => {
      const w = wrapper({ isReadOnly: true })
      w.find('a[title="change auto-update settings"]').simulate('click')
      expect(w.find('UpdateFrequencySelectModal')).toHaveLength(0)
    })

    it('does not open modal when anonymous', () => {
      const w = wrapper({ isAnonymous: true })
      w.find('a[title="change auto-update settings"]').simulate('click')
      expect(w.find('UpdateFrequencySelectModal')).toHaveLength(0)
    })
  })

  describe('connected to state', () => {
    let wrapper = null
    afterEach(() => {
      if (wrapper) {
        wrapper.unmount()
        wrapper = null
      }
    })

    const sampleState = {
      workflow: {
        id: 123,
        read_only: false,
        is_anonymous: false,
        tab_slugs: ['tab-11', 'tab-12']
      },
      tabs: {
        'tab-11': { wf_modules: [1, 212] }
      },
      wfModules: {
        1: { id: 1, tab_slug: 'tab-11', name: 'Ignore this one' },
        212: { id: 212, tab_slug: 'tab-11', auto_update_data: true, update_interval: 3600, update_units: 'days', notifications: false, last_update_check: '2018-05-28T19:00:54.154141Z' }
      }
    }

    it('should get settings from state', () => {
      const store = {
        getState: () => sampleState,
        dispatch: jest.fn(),
        subscribe: jest.fn()
      }
      wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect
            wfModuleId={212}
            lastCheckDate={null}
          />
        </Provider>
      )
      expect(wrapper.find('time').prop('dateTime')).toEqual('2018-05-28T19:00:54.154Z')
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      const modal = wrapper.find('UpdateFrequencySelectModal')
      expect(modal.prop('fetchInterval')).toBe(3600)
    })

    it('should not crash on a placeholder', () => {
      // can this even happen?
      const store = {
        getState: () => ({
          workflow: { id: 123, read_only: false, is_anonymous: false, wf_modules: ['nonce_212'] },
          wfModules: {}
        }),
        dispatch: jest.fn(),
        subscribe: jest.fn()
      }
      wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect
            wfModuleId={212}
          />
        </Provider>
      )
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      expect(true).toBe(true)
    })

    it('should set autofetch (calling API method)', () => {
      const api = {
        trySetWfModuleAutofetch: jest.fn(() => Promise.resolve({ isAutofetch: true, fetchInterval: 7200 }))
      }
      const store = mockStore(sampleState, api)
      wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect
            wfModuleId={212}
            lastCheckDate={null}
          />
        </Provider>
      )
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      const modal = wrapper.find('UpdateFrequencySelectModal')
      modal.prop('trySetAutofetch')(true, 7600)
      expect(api.trySetWfModuleAutofetch).toHaveBeenCalledWith(212, true, 7600)
    })

    it('should dispatch setNotifications (and call the API method)', () => {
      const api = {
        setWfModuleNotifications: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(sampleState, api)
      wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect
            wfModuleId={212}
            lastCheckDate={null}
          />
        </Provider>
      )
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      const modal = wrapper.find('UpdateFrequencySelectModal')
      modal.prop('setEmailUpdates')(false)
      expect(api.setWfModuleNotifications).toHaveBeenCalledWith(212, false)
    })
  })
})
