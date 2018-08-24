/* global describe, it, expect, jest */
import React from 'react'
import LoadingRefine, { Refine, RefineSpec } from './Refine'
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

  describe('RefineSpec', () => {
    // Most of this is untested because it's copy/pasted from our Python code
    // (which has unit tests). So the only possible errors are transcription
    // errors.

    describe('massRename', () => {
      function testMassRename (fromRenames, fromBlacklist, renames, toRenames, toBlacklist) {
        const fromSpec = new RefineSpec(fromRenames, fromBlacklist)
        const result = fromSpec.massRename(renames)
        const expected = new RefineSpec(toRenames, toBlacklist)
        expect(result.renames).toEqual(expected.renames)
        expect(result.blacklist.sort()).toEqual(expected.blacklist.sort())
      }

      it('should work in the simplest case', () => {
        testMassRename({}, [], { foo: 'bar' }, { foo: 'bar' }, [])
      })

      it('should rename an existing rename', () => {
        testMassRename({ a: 'b' }, [], { b: 'c' }, { a: 'c', b: 'c' }, [])
      })

      it('should rename a group that does not have its fromGroup as a member', () => {
        testMassRename(
          // Two groups: 'b' (contains original 'a') and 'c' (contains original 'b' and 'c')
          { a: 'b', b: 'c' }, [],
          // Rename group 'b'
          { b: 'd' },
          // New groups: 'd' (contains original 'a') and 'c' (contains original 'b' and 'c')
          { a: 'd', b: 'c' }, []
        )
      })

      it('should rename a group that does have its fromGroup as a member', () => {
        testMassRename(
          // Two groups: 'b' (contains original 'a') and 'c' (contains original 'b' and 'c')
          { a: 'b', b: 'c' }, [],
          // Rename group 'c'
          { c: 'd' },
          // New groups: 'b' (contains original 'a') and 'd' (contains original 'b' and 'c')
          { a: 'b', b: 'd', c: 'd' }, []
        )
      })

      it('should blacklist a new group if an old group is blacklisted', () => {
        testMassRename(
          { a: 'b' }, [ 'b' ],
          { b: 'c' },
          { a: 'c', b: 'c' }, [ 'c' ]
        )
      })

      it('should blacklist a new group if it was already blacklisted', () => {
        testMassRename(
          { a: 'b' }, [ 'c' ],
          { b: 'c' },
          { a: 'c', b: 'c' }, [ 'c' ]
        )
      })

      it('should swap two groups', () => {
        testMassRename(
          { a: 'x', b: 'x', c: 'y', d: 'y' }, [ 'x' ],
          { x: 'y', y: 'x' },
          { a: 'y', b: 'y', x: 'y', c: 'x', d: 'x', y: 'x' }, [ 'y' ]
        )
      })
    })
  })

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

  it('should show group values', () => {
    const w = wrapper({
      valueCounts: { 'a': 1, 'b': 1, 'c': 1 },
      value: JSON.stringify({ renames: { 'a': 'b' }, blacklist: [] })
    })

    expect(w.find('dd').at(0).text()).toEqual('') // collapsed to begin with

    // expand to see the values
    w.find('dt').at(0).find('input[name="expand"]').simulate('change', { target: { checked: true } })
    w.update()
    expect(w.find('dd').at(0).text()).toMatch(/a.*1.*b.*1/)

    // collapse to stop rendering them
    w.find('dt').at(0).find('label.expand input').simulate('change', { target: { checked: false } })
    w.update()
    expect(w.find('dd').at(0).text()).toEqual('') // collapsed to begin with
  })

  it('should un-group values', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, d: 1 },
      value: JSON.stringify({ renames: { a: 'c', b: 'c', d: 'e' }, blacklist: [] })
    })

    // expand to see the values:
    // a 1 [x]
    // b 1 [x]
    w.find('dt').at(0).find('input[name="expand"]').simulate('change', { target: { checked: true } })
    w.update()
    expect(w.find('dd').at(0).text()).toMatch(/a.*1.*b.*1/)

    w.find('button[name="reset"]').at(0).simulate('click')
    // The change is only applied _after_ we change the prop; outside of the
    // test environment, this is the Redux state.
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(JSON.parse(changeCalls[0][0]).renames).toEqual({ d: 'e' })
  })

  it('should un-group a single value', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, d: 1 },
      value: JSON.stringify({ renames: { a: 'c', b: 'c', d: 'e' }, blacklist: [] })
    })

    // expand to see the values:
    // a 1 [x]
    // b 1 [x]
    w.find('dt').at(0).find('input[name="expand"]').simulate('change', { target: { checked: true } })
    w.update()
    expect(w.find('dd').at(0).text()).toMatch(/a.*1.*b.*1/)

    w.find('.count-and-remove button[data-value="a"]').simulate('click')
    // The change is only applied _after_ we change the prop; outside of the
    // test environment, this is the Redux state.
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(JSON.parse(changeCalls[0][0]).renames).toEqual({ b: 'c', d: 'e' })
  })

  it('should not allow un-grouping a value from a group with the same name', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1 },
      value: JSON.stringify({ renames: { b: 'a' }, blacklist: [] })
    })

    // expand to see the values:
    // a 1 [ ]
    // b 1 [x]
    w.find('dt').at(0).find('input[name="expand"]').simulate('change', { target: { checked: true } })
    w.update()

    expect(w.find('.count-and-remove button[data-value="a"]')).toHaveLength(0)
  })

  it('should migrate a v0 spec', () => {
    // Previous versions of Refine had an awful spec with "select" and "change"
    // actions. See the "v0" stuff in `modules/refine.py` for further whinging.
    //
    // We need to migrate on the server side so renders continue to work when
    // users haven't edited params. _AND_ we need to migrate on the client side
    // so users can edit params. That's right: we need to write this migration
    // code and tests in two programming languages.
    //
    // So excuse me for not writing two identical barrages of unit tests. The
    // one test here will have to do.
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, d: 1 },
      value: JSON.stringify([
        { type: 'change', column: 'A', content: { fromVal: 'c', toVal: 'a' } },
        { type: 'select', column: 'A', content: { value: 'a' } }
      ])
    })

    expect(w.prop('onChange')).not.toHaveBeenCalled()

    // The 'a' group renders
    expect(w.find('dt input[type="text"]').at(0).prop('value')).toEqual('a')
    // The 'a' group is blacklisted
    expect(w.find('input[type="checkbox"]').at(0).prop('checked')).toBe(false)

    // Run _one_ action. Here, we choose, "un-blacklist a"
    w.find('input[type="checkbox"]').at(0).simulate('change', { target: { checked: true } })

    const onChangeCalls = w.prop('onChange').mock.calls
    expect(onChangeCalls).toHaveLength(1)
    expect(JSON.parse(onChangeCalls[0][0])).toEqual({
      renames: { c: 'a' },
      blacklist: []
    })
  })
})
