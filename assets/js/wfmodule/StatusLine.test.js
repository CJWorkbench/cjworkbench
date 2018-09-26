/* globals describe, it, expect */
import React from 'react'
import StatusLine from './StatusLine'
import { mount } from 'enzyme'

describe('Status line', () => {
  const wrapper = (extraProps) => {
    return mount(
      <StatusLine
        status='ready'
        error=''
        quickFixes={[]}
        applyQuickFix={jest.fn()}
        {...extraProps}
      />
    )
  }

  it('renders an error message', () => {
    const w = wrapper({ status: 'error', error: 'foo' })
    expect(w.find('p').text()).toEqual('foo')
  })

  it('renders a quick fix', () => {
    const w = wrapper({
      status: 'error',
      error: 'Wrong type',
      quickFixes: [
        {
          'text': 'Fix it',
          'action': 'prependModule',
          'args': [1, 2]
        }
      ]
    })

    expect(w.find('button').text()).toEqual('Fix it')
    w.find('button').simulate('click')
    expect(w.prop('applyQuickFix')).toHaveBeenCalledWith('prependModule', [1, 2])
  })

  it('renders null when no error', () => {
    const w = wrapper({ status: 'ready', error: '' })
    expect(w.text()).toBe(null)
  })
})
