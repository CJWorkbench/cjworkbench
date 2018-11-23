/* global describe, it, expect, jest */
import React from 'react'
import { mount } from 'enzyme'
import { ValueSelect } from './ValueSelect'
import { tick } from '../test-utils'

describe('ValueSelect', () => {
  const wrapper = (props={}) => mount(
    <ValueSelect
      valueCounts={{}}
      loading={false}
      value={''}
      onChange={jest.fn()}
      {...props}
    />
  )

  it('should render value texts in order', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 2 },
      value: ''
    })

    const value1 = w.find('.value').at(0)
    expect(value1.find('.text').text()).toEqual('a')
    expect(value1.find('.count').text()).toEqual('1')

    const value2 = w.find('.value').at(1)
    expect(value2.find('.text').text()).toEqual('b')
    expect(value2.find('.count').text()).toEqual('2')
  })

  it('should render commas in value counts', () => {
    const w = wrapper({
      valueCounts: { 'a': 1234 },
      value: ''
    })

    expect(w.find('.count').text()).toEqual('1,234')
  })

  it('should render when valueCounts have not loaded', () => {
    const w = wrapper({
      valueCounts: null,
      value: JSON.stringify({ 'a': 'b' })
    })

    expect(w.find('.text')).toHaveLength(0)
  })

  it('should show appropriate state', () => {
    const w = wrapper({
      valueCounts: { 'a': 2, 'b': 1 },
      value: JSON.stringify([ 'a' ])
    })

    // 'a': selected value ("shown" checkbox is checked)
    expect(w.find('.value').at(0).find('input[type="checkbox"]').prop('checked')).toBe(true)
    // 'b': not selected value ("shown" checkbox is unchecked)
    expect(w.find('.value').at(1).find('input[type="checkbox"]').prop('checked')).toBe(false)

    const changeCalls = w.prop('onChange').mock.calls

    // Add 'b' to selected values
    w.find('.value').at(1).find('input[type="checkbox"]').simulate('change', { target: { checked: true } })
    expect(changeCalls).toHaveLength(1)
    expect(JSON.parse(changeCalls[0][0])).toEqual([ 'a', 'b' ])

    // The change is only applied _after_ we change the prop; outside of the
    // test environment, this is the Redux state.
    // Cannot figure out how to test react-virtualized as per docs it requires a real DOM.
    // so remounting with return values
    const w2 = wrapper({
      valueCounts: { 'a': 2, 'b': 1 },
      value: changeCalls[0][0]
    })
    expect(w2.find('.value').at(1).find('input[type="checkbox"]').prop('checked')).toBe(true)
  })

  it('should find search results', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 1, 'd': 1 },
      value: JSON.stringify([])
    })

    expect(w.find('.value')).toHaveLength(5)

    w.find('input[type="search"]').simulate('change', { target: { value: 'b' }})
    w.update()
    expect(w.find('.value')).toHaveLength(2)
  })

  it('should set the value to [] when "None" pressed', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 1, 'd': 1},
      value: JSON.stringify([])
    })
    w.find('button[title="Select None"]').simulate('click')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(JSON.parse(changeCalls[0][0])).toEqual([])
  })

  it('should clear the blacklist when "All" pressed', () => {
    const w = wrapper({
      valueCounts: {'a': 1, 'b': 1, 'c': 1, 'bb': 1, 'd': 1},
      value: JSON.stringify(['a', 'b', 'd'])
    })

    w.find('button[title="Select All"]').simulate('click')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(JSON.parse(changeCalls[0][0])).toEqual(['a', 'b', 'c', 'bb', 'd'])
  })

  it('All and None buttons should be disabled when a search has taken place', () => {
    const w = wrapper({
      valueCounts: {'a': 1, 'b': 1, 'c': 1, 'BB': 1, 'd': 1},
      value: JSON.stringify(['a'])
    })

    w.find('input[type="search"]').simulate('change', {target: {value: 'a'}})
    w.update()
    expect(w.find('button[name="refine-select-all"]').prop('disabled')).toBe(true)
    expect(w.find('button[name="refine-select-none"]').prop('disabled')).toBe(true)

    // Select All should be disabled
    expect(w.find('button[title="Select All"]').prop('disabled')).toEqual(true)
    w.find('button[title="Select All"]').simulate('click')
    w.update()
    expect(w.prop('onChange').mock.calls).toHaveLength(0)

    // Select None should be disabled
    expect(w.find('button[title="Select None"]').prop('disabled')).toEqual(true)
    w.find('button[title="Select None"]').simulate('click')
    w.update()
    expect(w.prop('onChange').mock.calls).toHaveLength(0)
  })
})
