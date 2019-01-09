import React from 'react'
import UpdateFrequencySelectModal from './UpdateFrequencySelectModal'
import { shallow } from 'enzyme'

describe('UpdateFrequencySelectModal', () => {
  const defaultProps = {
    isAutoUpdate: false,
    isEmailUpdates: false,
    timeNumber: 1,
    timeUnit: 'days',
  }
  let onCancel
  let onSubmit

  const wrapper = (props={}) => {
    onCancel = jest.fn()
    onSubmit = jest.fn()
    return shallow(
      <UpdateFrequencySelectModal
        {...defaultProps}
        onCancel={onCancel}
        onSubmit={onSubmit}
        {...props}
        />
    )
  }

  it('should match snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('should disable inputs when not auto-update', () => {
    const w = wrapper({ isAutoUpdate: false })
    expect(w.find('Input[name="timeNumber"]').prop('disabled')).toBe(true)
    expect(w.find('Input[name="timeUnit"]').prop('disabled')).toBe(true)
    expect(w.find('Input[name="isEmailUpdates"]').prop('disabled')).toBe(true)
  })

  it('should enable inputs when changing to auto-update', () => {
    const w = wrapper({ isAutoUpdate: false })
    w.find('input[name="isAutoUpdate"][value="true"]').simulate('change', { target: { checked: true, value: 'true' } })
    expect(w.find('Input[name="timeNumber"]').prop('disabled')).toBe(false)
    expect(w.find('Input[name="timeUnit"]').prop('disabled')).toBe(false)
    expect(w.find('Input[name="isEmailUpdates"]').prop('disabled')).toBe(false)
  })

  it('should submit new values by form submit', () => {
    const w = wrapper({ isAutoUpdate: true })
    w.find('Input[name="timeNumber"]').simulate('change', { target: { value: '10' } })
    w.find('Input[name="timeUnit"]').simulate('change', { target: { value: 'hours' } })
    w.find('Input[name="isEmailUpdates"]').simulate('change', { target: { checked: true } })
    w.find('form').simulate('submit')
    expect(onCancel).not.toHaveBeenCalled()
    expect(onSubmit).toHaveBeenCalledWith({
      isAutoUpdate: true,
      timeNumber: 10,
      timeUnit: 'hours',
      isEmailUpdates: true,
    })
  })

  it('should not submit values when cancelling form', () => {
    const w = wrapper({ isAutoUpdate: true })
    w.find('Input[name="timeNumber"]').simulate('change', { target: { value: '10' } })
    w.find('form').simulate('cancel')
    expect(onCancel).toHaveBeenCalled()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('should treat submit as cancel if submitting unchanged values', () => {
    const w = wrapper({ isAutoUpdate: true, timeUnit: 'days', timeNumber: 10, isEmailUpdates: false })
    w.find('Input[name="timeUnit"]').simulate('change', { target: { value: 'minutes' } })
    w.find('Input[name="timeUnit"]').simulate('change', { target: { value: 'days' } })
    w.find('form').simulate('submit')
    expect(onCancel).toHaveBeenCalled()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
