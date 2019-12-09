/* globals describe, expect, it, jest */
import React from 'react'
import UpdateFrequencySelectModal from './UpdateFrequencySelectModal'
import { mountWithI18n } from '../../../i18n/test-utils'
import { tick } from '../../../test-utils'

describe('UpdateFrequencySelectModal', () => {
  const wrapper = (props = {}) => {
    return mountWithI18n(
      <UpdateFrequencySelectModal
        workflowId={123}
        wfModuleId={234}
        isAutofetch={false}
        fetchInterval={3600}
        isEmailUpdates={false}
        setEmailUpdates={jest.fn()}
        trySetAutofetch={jest.fn()}
        onClose={jest.fn()}
        {...props}
      />
    )
  }

  it('should match snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('should disable inputs when not auto-update', () => {
    const w = wrapper({ isAutofetch: false })
    expect(w.find('fieldset.fetch-interval').prop('disabled')).toBe(true)
  })

  it('should enable inputs when auto-update', () => {
    const w = wrapper({ isAutofetch: true })
    expect(w.find('fieldset.fetch-interval').prop('disabled')).toBe(false)
  })

  it('should show quotaExceeded and let user retry', async () => {
    // This is important because it lets the user change fetchInterval,
    // retry, and ultimately end up happy
    const w = wrapper({
      isAutofetch: false,
      trySetAutofetch: jest.fn(() => Promise.resolve({ value: { isAutofetch: false, fetchInterval: 3600, quotaExceeded: { maxFetchesPerDay: 500, nFetchesPerDay: 600, autofetches: [] } } }))
    })
    w.find('input[name="isAutofetch"][value="true"]').simulate('change', { target: { checked: true, value: 'true' } })
    expect(w.find('fieldset.autofetch').prop('disabled')).toBe(true) // we're submitting
    // Loop until fetch completes. (This is React 16.8. React 16.9 might do better)
    for (let i = 0; i < 10 && w.find('fieldset.autofetch').prop('disabled'); i++) {
      await tick()
      w.update() // async
    }
    expect(w.find('fieldset.autofetch').prop('disabled')).toBe(false) // we're done submitting
    expect(w.find('.quota-exceeded')).toHaveLength(1)
    expect(w.find('fieldset.fetch-interval').prop('disabled')).toBe(false) // user can edit autofetch stuff
  })
})
