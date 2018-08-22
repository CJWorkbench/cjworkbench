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
      allColumns={[{ name: 'A' }, { name: 'B' }, { name: 'C' }]}
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
    const w = wrapper({ value: 'A', prompt: 'Prompt!', allColumns: null })

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

  it('highlights prompt when value is invalid', async () => {
    const w = wrapper({ value: 'non-existent column' })
    await tick() // load columns
    w.update()

    // The browser will highlight the current value, even if it's disabled.
    expect(w.find('option.prompt').prop('value')).toEqual('non-existent column')
  })

  it('should retain double spaces in value', async () => {
    const w = wrapper({ value: 'column  with  double  spaces',
      allColumns: [{ name: 'column  with  double  spaces' }]})
    await tick() // load columns
    w.update()

    w.find('select').simulate('change')
    expect(w.prop('onChange')).toHaveBeenCalledWith('column  with  double  spaces')
  })
})
