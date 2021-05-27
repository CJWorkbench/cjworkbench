/* globals afterEach, beforeEach, describe, expect, it, jest */
import { mockStore } from '../../../test-utils'
import ConnectedUpdateFrequencySelect, {
  UpdateFrequencySelect
} from './UpdateFrequencySelect'
import { mountWithI18n } from '../../../i18n/test-utils'
import { Provider } from 'react-redux'

describe('UpdateFrequencySelect', () => {
  describe('shallow', () => {
    const defaultProps = {
      workflowId: 123,
      stepId: 212,
      isOwner: true,
      isAnonymous: false, // DELETEME
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

    const wrapper = extraProps => {
      return mountWithI18n(
        <UpdateFrequencySelect {...defaultProps} {...extraProps} />
      )
    }

    it('matches snapshot', () => {
      expect(wrapper()).toMatchSnapshot()
    })

    it('does not render modal on first load', () => {
      expect(wrapper().find('UpdateFrequencySelectModal')).toHaveLength(0)
    })

    it('does not open modal when not owner', () => {
      const w = wrapper({ isOwner: false })
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
      loggedInUser: { email: 'alice@example.com' },
      workflow: {
        id: 123,
        owner_email: 'alice@example.com',
        tab_slugs: ['tab-11', 'tab-12']
      },
      tabs: {
        'tab-11': { steps: [1, 212] }
      },
      steps: {
        1: { id: 1, tab_slug: 'tab-11', name: 'Ignore this one' },
        212: {
          id: 212,
          tab_slug: 'tab-11',
          auto_update_data: true,
          update_interval: 3600,
          update_units: 'days',
          notifications: false,
          last_update_check: '2018-05-28T19:00:54.154141Z'
        }
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
          <ConnectedUpdateFrequencySelect stepId={212} lastCheckDate={null} />
        </Provider>
      )
      const time = wrapper
        .find(
          'Trans[id="js.params.Custom.VersionSelect.UpdateFrequencySelect.lastChecked"]'
        )
        .prop('components')[0]
      expect(time.type).toEqual('time')
      expect(time.props.dateTime).toEqual('2018-05-28T19:00:54.154Z')
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      const modal = wrapper.find('UpdateFrequencySelectModal')
      expect(modal.prop('fetchInterval')).toBe(3600)
    })

    it('should not crash on a placeholder', () => {
      // can this even happen?
      const store = {
        getState: () => ({
          loggedInUser: { email: 'alice@example.com' },
          workflow: {
            id: 123,
            owner_email: 'alice@example.com',
            steps: ['nonce_212']
          },
          steps: {}
        }),
        dispatch: jest.fn(),
        subscribe: jest.fn()
      }
      wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect stepId={212} />
        </Provider>
      )
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      expect(true).toBe(true)
    })

    it('should set autofetch (calling API method)', () => {
      const api = {
        trySetStepAutofetch: jest.fn(() =>
          Promise.resolve({ isAutofetch: true, fetchInterval: 7200 })
        )
      }
      const store = mockStore(sampleState, api)
      wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect stepId={212} lastCheckDate={null} />
        </Provider>
      )
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      const modal = wrapper.find('UpdateFrequencySelectModal')
      modal.prop('trySetAutofetch')(true, 7600)
      expect(api.trySetStepAutofetch).toHaveBeenCalledWith(212, true, 7600)
    })

    it('should dispatch setNotifications (and call the API method)', () => {
      const api = {
        setStepNotifications: jest.fn(() => Promise.resolve(null))
      }
      const store = mockStore(sampleState, api)
      wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedUpdateFrequencySelect stepId={212} lastCheckDate={null} />
        </Provider>
      )
      wrapper.find('a[title="change auto-update settings"]').simulate('click')
      const modal = wrapper.find('UpdateFrequencySelectModal')
      modal.prop('setEmailUpdates')(false)
      expect(api.setStepNotifications).toHaveBeenCalledWith(212, false)
    })
  })
})
