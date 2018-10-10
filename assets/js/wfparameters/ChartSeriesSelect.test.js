/* global describe, it, expect, jest */
import React from 'react'
import ChartSeriesSelect from './ChartSeriesSelect'
import { mount } from 'enzyme'
import { sleep } from '../test-utils'

describe('ChartSeriesSelect', () => {
  function wrapper (props = {}) {
    return mount(
      <ChartSeriesSelect
        index={2}
        column='foo'
        color='#abcdef'
        isReadOnly={false}
        prompt={'prompt'}
        availableColumns={[{ name: 'foo' }, { name: 'bar' }]}
        onChange={jest.fn()}
        {...props}
      />
    )
  }

  /**
   * Sleep long enough for react-color's "onChangeComplete" to fire.
   *
   * Usage:
   *
   * async () => {
   *   wrapper.find('[color]').simulate('click')
   *   await sleepThroughDebounce()
   *   expect(callback).toHaveBeenCalled()
   * }
   */
  function sleepThroughDebounce () {
    return sleep(100)
  }

  it('should match snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('should change column', () => {
    const w = wrapper()
    w.find('ColumnParam').at(0).prop('onChange')('bar')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ index: 2, column: 'bar', color: '#abcdef' })
  })

  it('should change color', async () => {
    const w = wrapper()
    w.find('button[title="Pick color"]').simulate('click')
    w.find('div[title="#fbaa6d"]').simulate('click')
    await sleepThroughDebounce()
    expect(w.prop('onChange')).toHaveBeenCalledWith({ index: 2, column: 'foo', color: '#fbaa6d' })

    // test that picker disappears
    w.update()
    expect(w.find('div[title="#FBAA6D"]')).toHaveLength(0)
  })

  it('should postpone color change until column is set', async () => {
    const w = wrapper({ column: null, color: null })
    w.find('button[title="Pick color"]').simulate('click')
    w.update()
    w.find('div[title="#fbaa6d"]').simulate('click')
    await sleepThroughDebounce()
    expect(w.prop('onChange')).not.toHaveBeenCalled()
    w.find('ColumnParam[name="column"]').at(0).prop('onChange')('bar')
    expect(w.prop('onChange')).toHaveBeenCalledWith({ index: 2, column: 'bar', color: '#fbaa6d' })
  })
})
