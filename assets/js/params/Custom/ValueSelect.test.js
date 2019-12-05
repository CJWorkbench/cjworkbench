/* global describe, it, expect, jest */
import React from 'react'
import { mountWithI18n } from '../../i18n/test-utils'
import { ValueSelect } from './ValueSelect'

describe('ValueSelect', () => {
  const wrapper = (props = {}) => {
    const ret = mountWithI18n(
      <ValueSelect
        valueCounts={{}}
        loading={false}
        value={[]}
        onChange={jest.fn()}
        {...props}
      />
    )
    ret.update() // after componentDidMount()
    return ret
  }

  it('should render value texts in order', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 2 },
      value: []
    })

    const value1 = w.find('.value').at(0)
    expect(value1.find('.text').text()).toEqual('a')
    expect(value1.find('.count').text()).toEqual('1')

    const value2 = w.find('.value').at(1)
    expect(value2.find('.text').text()).toEqual('b')
    expect(value2.find('.count').text()).toEqual('2')
  })

  it('should render counts with SI suffixes', () => {
    const w = wrapper({
      valueCounts: { a: 1234, b: 234567890, c: 1000 },
      value: []
    })

    expect(w.find('.count').at(0).text()).toEqual('~1k')
    expect(w.find('.count').at(1).text()).toEqual('~235M')
    expect(w.find('.count').at(2).text()).toEqual('1k')
  })

  it('should render when valueCounts have not loaded', () => {
    const w = wrapper({
      valueCounts: null,
      value: ['a', 'b'],
      loading: true
    })

    expect(w.find('.text')).toHaveLength(0)
  })

  it('should show appropriate state (TODO rename this test)', () => {
    const w = wrapper({
      valueCounts: { a: 2, b: 1 },
      value: ['a']
    })

    // 'a': selected value ("shown" checkbox is checked)
    expect(w.find('.value').at(0).find('input[type="checkbox"]').prop('checked')).toBe(true)
    // 'b': not selected value ("shown" checkbox is unchecked)
    expect(w.find('.value').at(1).find('input[type="checkbox"]').prop('checked')).toBe(false)

    const changeCalls = w.prop('onChange').mock.calls

    // Add 'b' to selected values
    w.find('.value').at(1).find('input[type="checkbox"]').simulate('change', { target: { checked: true } })
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0]).toEqual(['a', 'b'])

    // The change is only applied _after_ we change the prop; outside of the
    // test environment, this is the Redux state.
    // Cannot figure out how to test react-virtualized as per docs it requires a real DOM.
    // so remounting with return values
    const w2 = wrapper({
      valueCounts: { a: 2, b: 1 },
      value: changeCalls[0][0]
    })
    expect(w2.find('.value').at(1).find('input[type="checkbox"]').prop('checked')).toBe(true)
  })

  it('should find search results', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, bb: 1, d: 1 },
      value: []
    })

    expect(w.find('.value')).toHaveLength(5)

    w.find('input[type="search"]').simulate('change', { target: { value: 'b' } })
    w.update()
    expect(w.find('.value')).toHaveLength(2)
  })

  it('should set the value to [] when "None" pressed', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, bb: 1, d: 1 },
      value: []
    })
    w.find('button[title="Select None"]').simulate('click')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0]).toEqual([])
  })

  it('should clear the blacklist when "All" pressed', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, bb: 1, d: 1 },
      value: ['a', 'b', 'd']
    })

    w.find('button[title="Select All"]').simulate('click')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].sort()).toEqual(['a', 'b', 'bb', 'c', 'd'])
  })

  it('should disable All and None buttons when a search has taken place', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, BB: 1, d: 1 },
      value: ['a']
    })

    w.find('input[type="search"]').simulate('change', { target: { value: 'a' } })
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

  it('should render without error when valueCounts = null', () => {
    const w = wrapper({
      valueCounts: null,
      value: []
    })
    // Used to throw TypeError
    w.setProps({ value: ['a'] })
  })
})
