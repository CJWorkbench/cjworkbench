/* global describe, it, expect, jest */
import React from 'react'
import Column from './Column'
import { mount } from 'enzyme'
import { tick } from '../test-utils'

describe('Column', () => {
  const wrapper = (props) => mount(
    <Column
      value={null}
      name='col'
      fieldId='col'
      placeholder='SelectACol'
      isReadOnly={false}
      inputColumns={[{ name: 'A' }, { name: 'B' }, { name: 'C' }]}
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
    const w = wrapper({ value: 'A', placeholder: 'Prompt!', inputColumns: null })

    // dropdown has 1 option, prompt as placeholder
    const select = w.find('Select')
    expect(select.prop('isLoading')).toBe(true)
    expect(select.prop('placeholder')).toBe('Prompt!')
  })

  it('renders a prompt', async () => {
    const w = wrapper({ value: 'A', placeholder: 'Prompt!' })
    await tick() // load columns
    w.update()

    // prompt appears as first option
    const select = w.find('Select')
    expect(select.prop('placeholder')).toBe('Prompt!')
  })

  it('lets the user choose an option', async () => {
    const w = wrapper({ value: null })
    await tick() // load columns
    w.update()

    w.find('Select').at(0).props().onChange({ value: 'B' })
    expect(w.prop('onChange')).toHaveBeenCalledWith('B')
  })

  // react-select should take care of this, but saving test in case there's an issue
  // it('highlights prompt when value is invalid', async () => {
  //  const w = wrapper({ value: 'non-existent column' })
  //  await tick() // load columns
  //  w.update()

  // The browser will highlight the current value, even if it's disabled.
  //  expect(w.find('option.prompt').prop('value')).toEqual('non-existent column')
  // })

  it('should retain double spaces in value', async () => {
    const w = wrapper({ value: 'column  with  double  spaces',
      inputColumns: [{ name: 'column  with  double  spaces' }] })
    await tick() // load columns
    w.update()

    w.find('Select').at(0).props().onChange({ value: 'column  with  double  spaces' })
    expect(w.prop('onChange')).toHaveBeenCalledWith('column  with  double  spaces')
  })
})
