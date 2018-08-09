/* global describe, it, expect, jest */
import React from 'react'
import LoadingRefine, { Refine } from './Refine'
import { mount } from 'enzyme'
import { tick } from '../test-utils'

describe('Refine', () => {
  const wrapper = (props={}) => mount(
    <Refine
      valueCounts={{}}
      loading={false}
      value={''}
      onChange={jest.fn()}
      {...props}
    />
  )

  it('should render value counts in order', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 2 },
      value: ''
    })

    const dt1 = w.find('dt').at(0)
    expect(dt1.find('input[type="text"]').prop('value')).toEqual('b')
    expect(dt1.find('.count').text()).toEqual('2')

    const dt2 = w.find('dt').at(1)
    expect(dt2.find('input[type="text"]').prop('value')).toEqual('a')
    expect(dt2.find('.count').text()).toEqual('1')
  })

  it('should render commas in value counts', () => {
    const w = wrapper({
      valueCounts: { 'a': 1234 },
      value: ''
    })

    expect(w.find('.count').text()).toEqual('1,234')
  })

  it('should render a rename', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 2 },
      value: JSON.stringify({ renames: { a: 'c' }, blacklist: [] })
    })

    expect(w.find('input[value="c"]')).toHaveLength(1)
  })

  it('should render when valueCounts have not loaded', () => {
    const w = wrapper({
      valueCounts: null,
      value: JSON.stringify({ renames: { 'a': 'b' }, blacklist: [] })
    })

    expect(w.find('input')).toHaveLength(0)
  })

  it('should blacklist', () => {
    const w = wrapper({
      valueCounts: { 'a': 2, 'b': 1 },
      value: JSON.stringify({ renames: {}, blacklist: [ 'a' ] })
    })

    // 'a': blacklisted ("shown" checkbox is unchecked)
    expect(w.find('dt').at(0).find('input[type="checkbox"]').prop('checked')).toBe(false)
    // 'b': not blacklisted ("shown" checkbox is checked)
    expect(w.find('dt').at(1).find('input[type="checkbox"]').prop('checked')).toBe(true)

    const changeCalls = w.prop('onChange').mock.calls

    // Add 'b' to blacklist
    w.find('dt').at(1).find('input[type="checkbox"]').simulate('change', { target: { checked: false } })
    expect(changeCalls).toHaveLength(1)
    expect(JSON.parse(changeCalls[0][0]).blacklist).toEqual([ 'a', 'b' ])

    // The change is only applied _after_ we change the prop; outside of the
    // test environment, this is the Redux state.
    w.update()
    expect(w.find('dt').at(1).find('input[type="checkbox"]').prop('checked')).toBe(true)
    w.setProps({ value: changeCalls[0][0] })
    w.update()
    expect(w.find('dt').at(1).find('input[type="checkbox"]').prop('checked')).toBe(false)

    // Remove 'b' from blacklist
    w.find('dt').at(1).find('input[type="checkbox"]').simulate('change', { target: { checked: true } })

    expect(changeCalls).toHaveLength(2)
    expect(JSON.parse(changeCalls[1][0]).blacklist).toEqual([ 'a' ])
  })

  it('should rename a value', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1 },
      value: JSON.stringify({ renames: {}, blacklist: [] })
    })

    w.find('input[value="a"]').simulate('change', { target: { value: 'b' } }).simulate('blur')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(JSON.parse(changeCalls[0][0]).renames).toEqual({ 'a': 'b' })
  })

  it('should re-rename a group', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1 },
      value: JSON.stringify({ renames: { 'a': 'b' }, blacklist: [] })
    })

    w.find('input[value="b"]').simulate('change', { target: { value: 'd' } }).simulate('blur')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(JSON.parse(changeCalls[0][0]).renames).toEqual({ 'a': 'd', 'b': 'd' })
  })
})
