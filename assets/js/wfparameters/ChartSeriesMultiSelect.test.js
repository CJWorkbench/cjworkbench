/* global describe, it, expect, jest */
import React from 'react'
import ChartSeriesMultiSelect from './ChartSeriesMultiSelect'
import { mount } from 'enzyme'
import { sleep, tick } from '../test-utils'

describe('ChartSeriesMultiSelect', () => {
  function wrapper (props = {}) {
    return mount(
      <ChartSeriesMultiSelect
        workflowRevision={1}
        series={[
          { column: 'A', color: '#aaaaaa' },
          { column: 'B', color: '#bbbbbb' }
        ]}
        fetchInputColumns={jest.fn(() => Promise.resolve([ 'A', 'B', 'C' ]))}
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

  it('should match snapshot', async () => {
    const w = wrapper()
    await tick() // load columns
    w.update()
    expect(w).toMatchSnapshot()
  })

  it('should change column', async () => {
    const w = wrapper()
    await tick() // load columns
    w.update()
    w.find('ChartSeriesSelect[column="B"] select[name="column"]').simulate('change', { target: { value: 'C' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith([
      { column: 'A', color: '#aaaaaa' },
      { column: 'C', color: '#bbbbbb' }
    ])
  })

  it('should add column', async () => {
    const w = wrapper()
    await tick() // load columns
    w.update()
    w.find('ChartSeriesSelect').at(2).find('select[name="column"]').simulate('change', { target: { value: 'C' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith([
      { column: 'A', color: '#aaaaaa' },
      { column: 'B', color: '#bbbbbb' },
      { column: 'C', color: '#48C8D7' }
    ])
  })

  it('should show loading', async () => {
    const w = wrapper()
    expect(w.find('p.loading')).toHaveLength(1)
  })

  it('should show error', async () => {
    const err = new Error('aww')
    const w = wrapper({ fetchInputColumns: jest.fn(() => Promise.reject(err)) })
    await tick() // load columns
    w.update()
    expect(w.find('p.error')).toHaveLength(1)
  })

  it('should reload columns', async () => {
    const fetchInputColumns = jest.fn()
    fetchInputColumns
      .mockReturnValueOnce(Promise.resolve([ 'A', 'B', 'C' ]))
      .mockReturnValue(Promise.resolve([ 'A', 'B', 'C', 'D' ]))
    const w = wrapper({ fetchInputColumns })
    await tick() // load columns
    w.update()
    w.setProps({ 'workflowRevision': 2 })
    expect(fetchInputColumns).toHaveBeenCalledTimes(2)
    await tick() // load columns again
    w.update()
    expect(w.find('ChartSeriesSelect[column="A"] option')).toHaveLength(4)
  })
})
