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

  it('renders and applies a quick fix', () => {
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

  it('prevents double-applying a quick fix', () => {
    const w = wrapper({
      status: 'error',
      error: 'Wrong type',
      quickFixes: [
        {
          'text': 'Fix it',
          'action': 'prependModule',
          'args': [1, 2]
        },
        {
          'text': 'Fix it more',
          'action': 'prependModule',
          'args': [2, 3]
        }
      ]
    })

    w.find('button').at(0).simulate('click')

    w.update()
    expect(w.find('button').at(0).prop('disabled')).toBe(true)
    expect(w.find('button').at(1).prop('disabled')).toBe(true)

    w.find('button').at(0).simulate('click')
    w.find('button').at(1).simulate('click')
    expect(w.prop('applyQuickFix')).not.toHaveBeenCalledTimes(2)
  })

  it('renders null when no error', () => {
    const w = wrapper({ status: 'ready', error: '' })
    expect(w.text()).toBe(null)
  })
})
