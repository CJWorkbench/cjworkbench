/* globals describe, expect, it, jest */
import React from 'react'
import StatusLine from './StatusLine'
import { mountWithI18n } from '../../i18n/test-utils'

describe('Status line', () => {
  const wrapper = (extraProps = {}) => {
    return mountWithI18n(
      <StatusLine
        isReadOnly={false}
        module={{ help_url: 'modules/foo' }}
        status='ok'
        errors={[]}
        applyQuickFix={jest.fn()}
        {...extraProps}
      />
    )
  }

  it('renders an error message', () => {
    const w = wrapper({ status: 'error', errors: [{ message: 'foo' }] })
    expect(w.find('p').text()).toEqual('foo')
  })

  it('renders and applies a quick fix', () => {
    const quickFix = {
      buttonText: 'Fix it',
      action: { type: 'prependStep', moduleSlug: 'dosomething', partialParams: { A: 'B' } }
    }
    const w = wrapper({
      status: 'error',
      errors: [{
        message: 'Wrong type',
        quickFixes: [quickFix]
      }]
    })

    expect(w.find('button').text()).toEqual('Fix it')
    w.find('button').simulate('click')
    expect(w.prop('applyQuickFix')).toHaveBeenCalledWith(quickFix.action)
  })

  it('shows error but not quick fixes if isReadOnly', () => {
    const quickFix = {
      buttonText: 'Fix it',
      action: { type: 'prependStep', moduleSlug: 'dosomething', partialParams: { A: 'B' } }
    }
    const w = wrapper({
      status: 'error',
      errors: [{
        message: 'Wrong type',
        quickFixes: [quickFix]
      }],
      isReadOnly: true
    })
    expect(w.find('p').text()).toEqual('Wrong type')
    expect(w.find('button')).toHaveLength(0)
  })

  it('prevents double-applying a quick fix', () => {
    const quickFix1 = {
      buttonText: 'Fix it',
      action: { type: 'prependStep', moduleSlug: 'dosomething', partialParams: { A: 'B' } }
    }
    const quickFix2 = {
      buttonText: 'Fix it more',
      action: { type: 'prependStep', moduleSlug: 'dosomething2', partialParams: { B: 'C' } }
    }
    const w = wrapper({
      status: 'error',
      errors: [{
        message: 'Wrong type',
        quickFixes: [quickFix1, quickFix2]
      }]
    })

    w.find('button').at(0).simulate('click')
    expect(w.find('button').at(0).prop('disabled')).toBe(true)
    expect(w.find('button').at(1).prop('disabled')).toBe(true)

    w.find('button').at(0).simulate('click')
    w.find('button').at(1).simulate('click')
    expect(w.prop('applyQuickFix')).not.toHaveBeenCalledTimes(2)
  })

  it('re-allows applying a quick fix when input changes', () => {
    // 1. Quick-fix to add something
    // 2. Click "Undo"
    //
    // expected results: you can quick fix again
    const quickFix = {
      buttonText: 'Fix it',
      action: { type: 'prependStep', moduleSlug: 'dosomething', partialParams: { A: 'B' } }
    }
    const errorProps = {
      status: 'error',
      errors: [{
        message: 'Wrong type',
        quickFixes: [quickFix]
      }]
    }

    const w = wrapper(errorProps)

    w.find('button').at(0).simulate('click')

    w.update()
    expect(w.find('button').at(0).prop('disabled')).toBe(true)

    w.setProps({ status: 'ok', errors: [] })
    w.setProps(errorProps)

    w.update()
    expect(w.find('button').at(0).prop('disabled')).toBe(false)
  })

  it('renders null when no error', () => {
    const w = wrapper({ status: 'ok', errors: [] })
    expect(w.html()).toEqual('')
  })
})
