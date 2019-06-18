import React from 'react'
import UpdateFrequencySelectModal from './UpdateFrequencySelectModal'
import { mount } from 'enzyme'

describe('UpdateFrequencySelectModal', () => {
  const wrapper = (props={}) => {
    return mount(
      <UpdateFrequencySelectModal
        isAutoUpdate={false}
        isEmailUpdates={false}
        timeNumber={1}
        timeUnit='days'
        onCancel={jest.fn()}
        onSubmit={jest.fn()}
        {...props}
      />
    )
  }

  it('should match snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('should disable inputs when not auto-update', () => {
    const w = wrapper({ isAutoUpdate: false })
    expect(w.find('input[name="timeNumber"]').prop('disabled')).toBe(true)
    expect(w.find('select[name="timeUnit"]').prop('disabled')).toBe(true)
    expect(w.find('input[name="isEmailUpdates"]').prop('disabled')).toBe(true)
  })

  it('should enable inputs when changing to auto-update', () => {
    const w = wrapper({ isAutoUpdate: false })
    w.find('input[name="isAutoUpdate"][value="true"]').simulate('change', { target: { checked: true, value: 'true' } })
    expect(w.find('input[name="timeNumber"]').prop('disabled')).toBe(false)
    expect(w.find('select[name="timeUnit"]').prop('disabled')).toBe(false)
    expect(w.find('input[name="isEmailUpdates"]').prop('disabled')).toBe(false)
  })

  it('should submit new values by form submit', () => {
    const w = wrapper({ isAutoUpdate: true })
    w.find('input[name="timeNumber"]').simulate('change', { target: { value: '10' } })
    w.find('select[name="timeUnit"]').simulate('change', { target: { value: 'hours' } })
    w.find('form').simulate('submit')
    expect(w.prop('onCancel')).not.toHaveBeenCalled()
    expect(w.prop('onSubmit')).toHaveBeenCalledWith({
      isAutoUpdate: true,
      timeNumber: 10,
      timeUnit: 'hours',
    })
  })

  it('should not submit values when cancelling form', () => {
    const w = wrapper({ isAutoUpdate: true })
    w.find('input[name="timeNumber"]').simulate('change', { target: { value: '10' } })
    w.find('form').simulate('reset')
    expect(w.prop('onCancel')).toHaveBeenCalled()
    expect(w.prop('onSubmit')).not.toHaveBeenCalled()
  })

  it('should treat submit as cancel if submitting unchanged values', () => {
    const w = wrapper({ isAutoUpdate: true, timeUnit: 'days', timeNumber: 10, isEmailUpdates: false })
    w.find('select[name="timeUnit"]').simulate('change', { target: { value: 'minutes' } })
    w.find('select[name="timeUnit"]').simulate('change', { target: { value: 'days' } })
    w.find('form').simulate('submit')
    expect(w.prop('onCancel')).toHaveBeenCalled()
    expect(w.prop('onSubmit')).not.toHaveBeenCalled()
  })
})
