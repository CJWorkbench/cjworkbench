/* global describe, it, expect, jest */
import React from 'react'
import ChartSeriesSelect from './ChartSeriesSelect'
import { mountWithI18n } from '../../i18n/test-utils'

describe('ChartSeriesSelect', () => {
  function wrapper (props = {}) {
    return mountWithI18n(
      <ChartSeriesSelect
        index={2}
        name='series[2]'
        fieldId='series_2'
        column='foo'
        color='#abcdef'
        isReadOnly={false}
        placeholder='placeholder'
        availableColumns={[{ name: 'foo' }, { name: 'bar' }]}
        onChange={jest.fn()}
        {...props}
      />
    )
  }

  it('should match snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('should change column', () => {
    const w = wrapper()
    w.find('ColumnParam').at(0).prop('onChange')('bar')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ index: 2, column: 'bar', color: '#abcdef' })
  })

  it('should change color', () => {
    const w = wrapper()
    w.find('button[title="Pick color"]').simulate('click')
    w.find('button[name="color-fbaa6d"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ index: 2, column: 'foo', color: '#fbaa6d' })

    // test that picker disappears
    w.update()
    expect(w.find('button[name="color-fbaa6d"]')).toHaveLength(0)
  })

  it('should postpone color change until column is set', () => {
    const w = wrapper({ column: null, color: null })
    w.find('button[title="Pick color"]').simulate('click')
    w.find('button[name="color-fbaa6d"]').simulate('click')
    expect(w.prop('onChange')).not.toHaveBeenCalled()
    w.find('ColumnParam[fieldId="series_2_column"]').at(0).prop('onChange')('bar')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ index: 2, column: 'bar', color: '#fbaa6d' })
  })
})
