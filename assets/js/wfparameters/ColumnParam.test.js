/* global describe, it, expect, jest */
import React from 'react'
import ColumnParam from './ColumnParam'
import { mount } from 'enzyme'
import { tick } from '../test-utils'

describe('ColumnParam', () => {
  const wrapper = (props) => mount(
    <ColumnParam
      value={null}
      name='col'
      prompt='SelectACol'
      isReadOnly={false}
      workflowRevision={1}
      fetchInputColumns={jest.fn(() => Promise.resolve(['A', 'B', 'C']))}
      onChange={jest.fn()}
      {...props}
    />
  )

  it('matches snapshot', async () => {
    const w = wrapper({ value: null })
    await tick() // load columns
    w.update()
    expect(w).toMatchSnapshot()
  })

  it('renders loading', () => {
    const w = wrapper({ value: 'A', prompt: 'Prompt!' })

    // select has "loading" class
    expect(w.find('select.loading')).toHaveLength(1)

    // prompt appears as first option
    const promptOption = w.find('option').at(0)
    expect(promptOption.text()).toEqual('Prompt!')
    expect(promptOption.is('.prompt')).toBe(true)
    expect(promptOption.prop('disabled')).toBe(true)

    // loading appears below
    const loadingOption = w.find('option').at(1)
    expect(loadingOption.prop('disabled')).toBe(true)
    expect(loadingOption.is('.loading')).toBe(true)
  })

  it('renders a prompt', async () => {
    const w = wrapper({ value: 'A', prompt: 'Prompt!' })
    await tick() // load columns
    w.update()

    // prompt appears as first option
    const promptOption = w.find('option').at(0)
    expect(promptOption.is('.prompt')).toBe(true)
    expect(promptOption.text()).toEqual('Prompt!')
    expect(promptOption.prop('disabled')).toBe(true)
  })

  it('lets the user choose an option', async () => {
    const w = wrapper({ value: null })
    await tick() // load columns
    w.update()

    w.find('select').simulate('change', { target: { value: 'B' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith('B')
  })

  it('renders an error', async () => {
    const fetchInputColumns = jest.fn()
    fetchInputColumns.mockReturnValue(Promise.reject(new Error('FOO!')))
    const w = wrapper({ fetchInputColumns })
    await tick() // load columns
    w.update()

    expect(w.find('option')).toHaveLength(1) // nothing but error
    expect(w.find('option.error')).toHaveLength(1)
  })

  it('re-fetches colnames on revision change', async () => {
    const fetchInputColumns = jest.fn()
    fetchInputColumns
      .mockReturnValueOnce(Promise.resolve([ 'A', 'B' ]))
      .mockReturnValueOnce(Promise.resolve([ 'A', 'C' ]))
      .mockReturnValue(Promise.resolve([ 'A', 'D' ]))
    const w = wrapper({ fetchInputColumns })
    await tick() // load columns
    w.update()

    w.setProps({ workflowRevision: 2 }) // trigger update
    await tick() // load columns
    w.update()

    expect(w.find('option').last().text()).toEqual('C')

    w.setProps({ prompt: 'something else' }) // do NOT trigger update
    await tick() // no-op, but we need it in the test to prove nothing changed
    w.update()
    expect(w.find('option').last().text()).toEqual('C') // not D
  })

  it('highlights prompt when value is invalid', async () => {
    const w = wrapper({ value: 'non-existent column' })
    await tick() // load columns
    w.update()

    // The browser will highlight the current value, even if it's disabled.
    expect(w.find('option.prompt').prop('value')).toEqual('non-existent column')
  })
})
