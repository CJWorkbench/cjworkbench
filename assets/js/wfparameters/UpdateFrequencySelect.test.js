jest.mock('../WorkbenchAPI', () => {
  return {
    updateWfModule: jest.fn(),
  }
})

import { mockStore } from '../workflow-reducer'
import React from 'react'
import ConnectedUpdateFrequencySelect, { UpdateFrequencySelect } from './UpdateFrequencySelect'
import { shallow, mount } from 'enzyme'
import { Provider } from 'react-redux'
import WorkbenchAPI from '../WorkbenchAPI'

describe('UpdateFrequencySelect', () => {
  describe('shallow', () => {
    const defaultProps = {
      wfModuleId: 212,
      isReadOnly: false,
      isAnonymous: false,
      lastCheckDate: new Date(Date.parse('2018-05-28T19:00:54.154Z')),
      settings: {
        isAutoUpdate: false, // start in Manual mode
        isEmailUpdates: false,
        timeNumber: 5,
        timeUnit: 'minutes',
      },
    }

    let dateSpy
    beforeEach(() => {
      dateSpy = jest.spyOn(Date, 'now').mockImplementation(() => 1527534812631)
    })
    afterEach(() => dateSpy.mockRestore())

    let updateSettings

    const wrapper = (extraProps) => {
      updateSettings = jest.fn()

      const oldDateNow = Date.now
      return shallow(
        <UpdateFrequencySelect
          {...defaultProps}
          updateSettings={updateSettings}
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

    it('submits modal', () => {
      const w = wrapper()
      const newSettings = {
        isAutoUpdate: true,
        isEmailUpdates: false,
        timeNumber: 10,
        timeUnit: 'minutes',
      }
      w.find('a[title="change auto-update settings"]').simulate('click')
      w.find('UpdateFrequencySelectModal').prop('onSubmit')(newSettings)
      expect(updateSettings).toHaveBeenCalledWith(newSettings)
      w.update()
      expect(w.find('UpdateFrequencySelectModal')).toHaveLength(0)
    })

    it('cancels modal', () => {
      const w = wrapper()
      w.find('a[title="change auto-update settings"]').simulate('click')
      w.find('UpdateFrequencySelectModal').prop('onCancel')()
      expect(updateSettings).not.toHaveBeenCalled()
      w.update()
      expect(w.find('UpdateFrequencySelectModal')).toHaveLength(0)
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
        read_only: false,
        is_anonymous: false,
        wf_modules: [ 1, 212 ]
      },
      wfModules: {
        1: { id: 1, name: 'Ignore this one' },
        212: { id: 212, auto_update_data: true, update_interval: 10, update_units: 'days', notifications: false, last_update_check: '2018-05-28T19:00:54.154141Z' }
      }
    }

    it('should get settings from state', () => {
      const store = {
        getState: () => sampleState,
        dispatch: jest.fn(),
        subscribe: jest.fn(),
      }
      wrapper = mount(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect
            wfModuleId={212}
            lastCheckDate={null}
            />
        </Provider>
      )
      expect(wrapper.find('time').prop('time')).toEqual('2018-05-28T19:00:54.154Z')
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      const modal = wrapper.find('UpdateFrequencySelectModal')
      expect(modal.prop('timeNumber')).toBe(10)
    })

    it('should not crash on a placeholder', () => {
      // can this even happen?
      const store = {
        getState: () => ({
          workflow: { read_only: false, is_anonymous: false, wf_modules: [ 'nonce_212' ] },
          wfModules: {}
        }),
        dispatch: jest.fn(),
        subscribe: jest.fn(),
      }
      wrapper = mount(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect
            wfModuleId={212}
            />
        </Provider>
      )
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      expect(true).toBe(true)
    })

    it('should dispatch an update (and call the API method)', () => {
      const store = mockStore(sampleState)
      wrapper = mount(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect
            wfModuleId={212}
            lastCheckDate={null}
            />
        </Provider>
      )
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      const modal = wrapper.find('UpdateFrequencySelectModal')
      modal.prop('onSubmit')({
        isAutoUpdate: true,
        isEmailUpdates: true,
        timeNumber: 2,
        timeUnit: 'days',
      })
      expect(WorkbenchAPI.updateWfModule).toHaveBeenCalledWith(212, {
        auto_update_data: true,
        notifications: true,
        update_interval: 2,
        update_units: 'days',
      })
    })
  })
})
