/* globals describe, expect, it, jest */
import React from 'react'
import { mountWithI18n } from '../../i18n/test-utils'
import ValueSortSelect from './ValueSortSelect'

describe('ValueSortSelect', () => {
  const wrapper = (extraProps = {}) => mountWithI18n(
    <ValueSortSelect
      value={{ by: 'value', isAscending: false }}
      onChange={jest.fn()}
      {...extraProps}
    />
  )

  it('should invert sort by value', () => {
    const w = wrapper({ value: { by: 'value', isAscending: true } })
    w.find('button[name="by-value"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ by: 'value', isAscending: false })
  })

  it('should default sort-by-value to ascending', () => {
    const w = wrapper({ value: { by: 'count', isAscending: true } })
    w.find('button[name="by-value"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ by: 'value', isAscending: true })
  })

  it('should invert sort by count', () => {
    const w = wrapper({ value: { by: 'count', isAscending: true } })
    w.find('button[name="by-count"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ by: 'count', isAscending: false })
  })

  it('should default sort-by-count to descending', () => {
    const w = wrapper({ value: { by: 'value', isAscending: true } })
    w.find('button[name="by-count"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ by: 'count', isAscending: false })
  })
})
