/* global describe, it, expect, jest */
import React from 'react'
import LoadingRefine, { Refine, RefineSpec } from './index'
import { mount } from 'enzyme'
import { tick } from '../../../test-utils'

const DefaultValue = { renames: {} }

describe('Refine', () => {
  const wrapper = (props={}) => mount(
    <Refine
      valueCounts={{}}
      loading={false}
      value={DefaultValue}
      onChange={jest.fn()}
      {...props}
    />
  )

  describe('RefineSpec', () => {
    // Most of this is untested because it's copy/pasted from our Python code
    // (which has unit tests). So the only possible errors are transcription
    // errors.

    describe('massRename', () => {
      function testMassRename (fromRenames, renames, toRenames) {
        const fromSpec = new RefineSpec(fromRenames)
        const result = fromSpec.massRename(renames)
        const expected = new RefineSpec(toRenames)
        expect(result.renames).toEqual(expected.renames)
      }

      it('should work in the simplest case', () => {
        testMassRename({}, { foo: 'bar' }, { foo: 'bar' })
      })

      it('should rename an existing rename', () => {
        testMassRename({ a: 'b' }, { b: 'c' }, { a: 'c', b: 'c' })
      })

      it('should rename a group that does not have its fromGroup as a member', () => {
        testMassRename(
          // Two groups: 'b' (contains original 'a') and 'c' (contains original 'b' and 'c')
          { a: 'b', b: 'c' },
          // Rename group 'b'
          { b: 'd' },
          // New groups: 'd' (contains original 'a') and 'c' (contains original 'b' and 'c')
          { a: 'd', b: 'c' }
        )
      })

      it('should rename a group that does have its fromGroup as a member', () => {
        testMassRename(
          // Two groups: 'b' (contains original 'a') and 'c' (contains original 'b' and 'c')
          { a: 'b', b: 'c' },
          // Rename group 'c'
          { c: 'd' },
          // New groups: 'b' (contains original 'a') and 'd' (contains original 'b' and 'c')
          { a: 'b', b: 'd', c: 'd' }
        )
      })

      it('should swap two groups', () => {
        testMassRename(
          { a: 'x', b: 'x', c: 'y', d: 'y' },
          { x: 'y', y: 'x' },
          { a: 'y', b: 'y', x: 'y', c: 'x', d: 'x', y: 'x' }
        )
      })
    })
  })

  it('should render value counts in order', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 2 },
      value: DefaultValue
    })

    const dt1 = w.find('.summary').at(0)
    expect(dt1.find('input[type="text"]').prop('value')).toEqual('b')
    expect(dt1.find('.count').text()).toEqual('2')

    const dt2 = w.find('.summary').at(1)
    expect(dt2.find('input[type="text"]').prop('value')).toEqual('a')
    expect(dt2.find('.count').text()).toEqual('1')
  })

  it('should render commas in value counts', () => {
    const w = wrapper({
      valueCounts: { 'a': 1234 },
      value: DefaultValue
    })

    expect(w.find('.count').text()).toEqual('1,234')
  })

  it('should render a rename', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 2 },
      value: { renames: { a: 'c' } }
    })

    expect(w.find('input[value="c"]')).toHaveLength(1)
  })

  it('should render when valueCounts have not loaded', () => {
    const w = wrapper({
      valueCounts: null,
      value: { renames: { 'a': 'b' } }
    })

    expect(w.find('input')).toHaveLength(0)
  })

  it('should rename a value', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1 },
      value: { renames: {} }
    })

    w.find('input[value="a"]').simulate('change', { target: { value: 'b' } }).simulate('blur')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({ 'a': 'b' })
  })

  it('should re-rename a group', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1 },
      value: { renames: { 'a': 'b' } }
    })

    w.find('input[value="b"]').simulate('change', { target: { value: 'd' } }).simulate('blur')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({ 'a': 'd', 'b': 'd' })
  })

  it('should show group values', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1 },
      value: { renames: { 'a': 'b' } }
    })

    expect(w.find('.values')).toHaveLength(0) // collapsed to begin with

    // expand to see the values
    w.find('.summary').at(0).find('input[name="expand"]').simulate('change', { target: { checked: true } })
    w.update()
    expect(w.find('.values').at(0).text()).toMatch(/a.*1.*b.*1/)

    // collapse to stop rendering them
    w.find('.summary').at(0).find('label.expand input').simulate('change', { target: { checked: false } })
    w.update()
    expect(w.find('.values')).toHaveLength(0) // collapsed to begin with
  })

  it('should un-group values', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, d: 1 },
      value: { renames: { a: 'c', b: 'c', d: 'e' } }
    })

    // expand to see the values:
    // a 1 [x]
    // b 1 [x]
    w.find('.summary').at(0).find('input[name="expand"]').simulate('change', { target: { checked: true } })
    w.update()
    expect(w.find('.values').at(0).text()).toMatch(/a.*1.*b.*1/)

    w.find('button[name="reset"]').at(0).simulate('click')
    // The change is only applied _after_ we change the prop; outside of the
    // test environment, this is the Redux state.
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({ d: 'e' })
  })

  it('should un-group a single value', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, d: 1 },
      value: { renames: { a: 'c', b: 'c', d: 'e' } }
    })

    // expand to see the values:
    // a 1 [x]
    // b 1 [x]
    w.find('.summary').at(0).find('input[name="expand"]').simulate('change', { target: { checked: true } })
    w.update()
    expect(w.find('.values').at(0).text()).toMatch(/a.*1.*b.*1/)

    w.find('.count-and-remove button[data-value="a"]').simulate('click')
    // The change is only applied _after_ we change the prop; outside of the
    // test environment, this is the Redux state.
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({ b: 'c', d: 'e' })
  })

  it('should not allow un-grouping a value from a group with the same name', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1 },
      value: { renames: { b: 'a' } }
    })

    // expand to see the values:
    // a 1 [ ]
    // b 1 [x]
    w.find('.summary').at(0).find('input[name="expand"]').simulate('change', { target: { checked: true } })
    w.update()

    expect(w.find('.count-and-remove button[data-value="a"]')).toHaveLength(0)
  })

  it('should find search results within both group names and members', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 1, 'd': 1},
      value: { renames: { 'c': 'b', 'bb': 'a' } }
    })
    // Ensure 3 groups initially rendered
    expect(w.find('.visible').children()).toHaveLength(3)

    w.find('input[type="search"]').simulate('change', {target: {value: 'b'}})
    w.update()
    expect(w.find('.visible')).toHaveLength(2)
  })

  it('should uncheck all _search results_ when "None" pressed', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 1, 'd': 1 },
      value: { renames: {} }
    })
    w.find('input[type="checkbox"]').forEach(obj => {
      obj.simulate('change', { target: { checked: true } })
    })

    expect(w.find('input[checked=true]')).toHaveLength(5)
    w.find('input[type="search"]').simulate('change', {target: {value: 'b'}})
    w.update()

    w.find('button[title="Select None"]').simulate('click')
    w.find('input[type="search"]').simulate('change', {target: {value: ''}})
    expect(w.find('input[checked=true]')).toHaveLength(3)

    //Now clear the rest with no search input
    w.find('button[title="Select None"]').simulate('click')
    expect(w.find('input[checked=true]')).toHaveLength(0)
  })

  it('should check all _search results_ when "All" pressed', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 1, 'd': 1 },
      value: { renames: {} }
    })

    expect(w.find('input[checked=true]')).toHaveLength(0)
    w.find('input[type="search"]').simulate('change', {target: {value: 'b'}})
    w.update()

    w.find('button[title="Select All"]').simulate('click')
    w.find('input[type="search"]').simulate('change', {target: {value: ''}})
    expect(w.find('input[checked=true]')).toHaveLength(2)

    //Now select the rest with no search input
    w.find('button[title="Select All"]').simulate('click')
    expect(w.find('input[checked=true]')).toHaveLength(5)
  })

  it('should disable merge button when less than 2 values selected', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 1, 'd': 1},
      value: { renames: { } }
    })
    expect(w.find('button[name="merge"]').prop('disabled')).toEqual(true)
    w.find('.summary').at(0).find('input[type="checkbox"]').simulate('change',{ target: { checked: true } })
    w.find('.summary').at(1).find('input[type="checkbox"]').simulate('change',{ target: { checked: true } })
    expect(w.find('button[name="merge"]').prop('disabled')).toEqual(false)
  })

  it('should merge values into one group when checked and merge button pressed', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 2, 'd': 1},
      value: { renames: { } }
    })
    w.find('input[name="include[b]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="include[bb]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({"b": "bb", "bb": "bb"})
  })

  /*
      Default value order rules:
      1. Group 'values' count
      2. Group 'count'
      3. Alphabetical
   */
  it('should merge values to default value based on rules', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 2, 'd': 1, 'e': 2, 'f': 1},
      value: { renames: { 'bb': 'a' } }
    })
    // Group 'value' count
    w.find('input[name="include[a]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="include[b]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({"a": "a", "b": "a", "bb": "a"})

    // Group count
    w.setProps({value: { renames: {} }})
    w.find('input[name="include[c]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="include[e]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    expect(changeCalls).toHaveLength(2)
    expect(changeCalls[1][0].renames).toEqual({"e": "e", "c": "e"})

    // Alphabetical
    w.setProps({value: { renames: {} }})
    w.find('input[name="include[f]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="include[d]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    expect(changeCalls).toHaveLength(3)
    expect(changeCalls[2][0].renames).toEqual({"f": "d", "d": "d"})
  })
  it('should focus the new group text for editing after merge', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1, 'bb': 2, 'd': 1, 'e': 2, 'f': 1},
      value: { renames: { 'bb': 'a' } }
    })

    w.find('input[name="include[a]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="include[b]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    expect(document.activeElement['value']).toBe('a')
  })
})
