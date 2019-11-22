/* global describe, it, expect, jest */
import React from 'react'
import { Refine } from './index'
import { mountWithI18n } from '../../../i18n/test-utils'

const DefaultValue = { renames: {} }

describe('Refine', () => {
  const wrapper = (props = {}) => {
    const ret = mountWithI18n(
      <Refine
        valueCounts={{}}
        loading={false}
        value={DefaultValue}
        onChange={jest.fn()}
        {...props}
      />
    )
    ret.update() // after componentDidMount() -- does size calculations
    return ret
  }

  it('should render groups counts in order', () => {
    const w = wrapper({
      valueCounts: { b: 2, a: 1 },
      value: DefaultValue
    })

    const dt1 = w.find('.summary').at(0)
    expect(dt1.find('input[type="text"]').prop('value')).toEqual('a')
    expect(dt1.find('.count').text()).toEqual('1')

    const dt2 = w.find('.summary').at(1)
    expect(dt2.find('input[type="text"]').prop('value')).toEqual('b')
    expect(dt2.find('.count').text()).toEqual('2')
  })

  it('should render counts with SI suffixes', () => {
    const w = wrapper({
      valueCounts: { a: 1234, b: 234567890, c: 1000 },
      value: DefaultValue
    })

    expect(w.find('.count').at(0).text()).toEqual('~1k')
    expect(w.find('.count').at(1).text()).toEqual('~235M')
    expect(w.find('.count').at(2).text()).toEqual('1k')
  })

  it('should render a rename', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 2 },
      value: { renames: { a: 'c' } }
    })

    expect(w.find('input[value="c"]')).toHaveLength(1)
  })

  it('should render when valueCounts have not loaded', () => {
    const w = wrapper({
      valueCounts: null,
      value: { renames: { a: 'b' } }
    })

    expect(w.find('input')).toHaveLength(0)
  })

  it('should rename a value', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1 },
      value: { renames: {} }
    })

    w.find('input[value="a"]').simulate('change', { target: { value: 'b' } }).simulate('blur')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({ a: 'b' })
  })

  it('should re-rename a group', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1 },
      value: { renames: { a: 'b' } }
    })

    w.find('input[value="b"]').simulate('change', { target: { value: 'd' } }).simulate('blur')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({ a: 'd', b: 'd' })
  })

  it('should show group values', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1 },
      value: { renames: { a: 'b' } }
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
      valueCounts: { a: 1, b: 1, c: 1, bb: 1, d: 1 },
      value: { renames: { c: 'b', bb: 'a' } }
    })
    // Ensure 3 groups initially rendered
    expect(w.find('.refine-group')).toHaveLength(3)

    w.find('input[type="search"]').simulate('change', { target: { value: 'b' } })
    w.update()
    expect(w.find('.refine-group')).toHaveLength(2)
  })

  it('should uncheck all _search results_ when "None" pressed', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, bb: 1, d: 1 },
      value: { renames: {} }
    })
    w.find('input[type="checkbox"]').forEach(obj => {
      obj.simulate('change', { target: { checked: true } })
    })

    expect(w.find('input[checked=true]')).toHaveLength(5)
    w.find('input[type="search"]').simulate('change', { target: { value: 'b' } })
    w.update()

    w.find('button[title="Select None"]').simulate('click')
    w.find('input[type="search"]').simulate('change', { target: { value: '' } })
    expect(w.find('input[checked=true]')).toHaveLength(3)
  })

  it('should uncheck everything when "None" pressed with no search', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1 },
      value: { renames: {} }
    })
    w.find('input[type="checkbox"]').forEach(obj => {
      obj.simulate('change', { target: { checked: true } })
    })

    expect(w.find('input[checked=true]')).toHaveLength(3)
    w.find('button[title="Select None"]').simulate('click')
    expect(w.find('input[checked=true]')).toHaveLength(0)
  })

  it('should check all _search results_ when "All" pressed', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, bb: 1, d: 1 },
      value: { renames: {} }
    })

    expect(w.find('input[checked=true]')).toHaveLength(0)
    w.find('input[type="search"]').simulate('change', { target: { value: 'b' } })
    w.update()

    w.find('button[title="Select All"]').simulate('click')
    w.find('input[type="search"]').simulate('change', { target: { value: '' } })
    expect(w.find('input[checked=true]')).toHaveLength(2)
  })

  it('should check everything when "All" pressed with no search', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1 },
      value: { renames: {} }
    })

    expect(w.find('input[checked=true]')).toHaveLength(0)
    w.find('button[title="Select All"]').simulate('click')
    expect(w.find('input[checked=true]')).toHaveLength(3)
  })

  it('should disable merge button when less than 2 values selected', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, bb: 1, d: 1 },
      value: { renames: { } }
    })
    expect(w.find('button[name="merge"]').prop('disabled')).toEqual(true)
    w.find('.summary').at(0).find('input[type="checkbox"]').simulate('change', { target: { checked: true } })
    w.find('.summary').at(1).find('input[type="checkbox"]').simulate('change', { target: { checked: true } })
    expect(w.find('button[name="merge"]').prop('disabled')).toEqual(false)
  })

  it('should merge values into one group when checked and merge button pressed', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, bb: 2, d: 1 },
      value: { renames: { } }
    })
    w.find('input[name="select[b]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="select[bb]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({ b: 'bb' })
  })

  it('should choose group name by count when merging', () => {
    const w = wrapper({
      valueCounts: { a: 4, b: 1, c: 2 },
      value: { renames: { b: 'c' } } // a: 4, c: 3 (in 2 groups)
    })
    // Group 'value' count
    w.find('input[name="select[a]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="select[c]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    const changeCalls = w.prop('onChange').mock.calls
    expect(changeCalls).toHaveLength(1)
    expect(changeCalls[0][0].renames).toEqual({ b: 'a', c: 'a' })
  })

  it('should choose group name by nValues when merging and count is equal', () => {
    const w = wrapper({
      valueCounts: { a: 2, b: 1, c: 1 },
      value: { renames: { b: 'c' } } // a: 2, c: 2 (from 2 groups)
    })
    w.find('input[name="select[a]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="select[c]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ renames: { a: 'c', b: 'c' } })
  })

  it('should choose group name alphabetically when merging and count+nValues are equal', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1, d: 1 },
      value: { renames: { b: 'a', c: 'd' } } // a: 2, d: 2
    })
    w.find('input[name="select[a]"]').simulate('change', { target: { checked: true } })
    w.find('input[name="select[d]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ renames: { b: 'a', c: 'a', d: 'a' } })
  })

  it('should focus the new group text for editing after merge', () => {
    const w = wrapper({
      valueCounts: { a: 1, b: 1, c: 1 },
      value: { renames: { b: 'a' } }
    })

    w.find('input[name="select[a]"]').simulate('change', { target: { checked: true } })
    // focus 'c'
    w.find('input[name="select[c]"]').simulate('change', { target: { checked: true } })
    w.find('button[name="merge"]').simulate('click')
    expect(document.activeElement.value).toBe('a')
  })
})
