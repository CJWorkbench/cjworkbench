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
        isReadOnly={false}
        prompt={'prompt'}
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

  it('should add a column', async () => {
    const w = wrapper()
    await tick() // load columns
    w.update()
    w.find('button[title="add another column"]').simulate('click')
    w.find('ChartSeriesSelect').at(2).find('select[name="column"]').simulate('change', { target: { value: 'C' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith([
      { column: 'A', color: '#aaaaaa' },
      { column: 'B', color: '#bbbbbb' },
      { column: 'C', color: '#fbaa6d' }
    ])
  })

  it('should present a placeholder when empty', async () => {
    const w = wrapper({ series: [] })
    await tick() // load columns
    w.update()
    expect(w.find('ChartSeriesSelect')).toHaveLength(1)
    // No add/remove buttons
    expect(w.find('button[title="add another column"]')).toHaveLength(0)
    expect(w.find('button[title="remove last column"]')).toHaveLength(0)
  })

  it('should remove a column', async () => {
    const w = wrapper()
    await tick() // load columns
    w.update()
    w.find('button[title="remove last column"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith([
      { column: 'A', color: '#aaaaaa' }
    ])
  })

  it('should remove placeholder, not column, if placeholder selected', async () => {
    const w = wrapper()
    await tick() // load columns
    w.update()
    w.find('button[title="add another column"]').simulate('click')
    w.find('button[title="remove last column"]').simulate('click')
    expect(w.find('ChartSeriesSelect')).toHaveLength(2)
    expect(w.prop('onChange')).not.toHaveBeenCalled()
  })

  it('should not allow removing last column', async () => {
    const w = wrapper({ series: [
      { column: 'A', color: '#aaaaaa' }
    ]})
    await tick() // load columns
    w.update()
    expect(w.find('button[title="remove last column"]')).toHaveLength(0)
  })

  it('should not allow adding two placeholders', async () => {
    const w = wrapper()
    await tick() // load columns
    w.update()
    w.find('button[title="add another column"]').simulate('click')
    expect(w.find('button[title="add another column"]')).toHaveLength(0)
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
    expect(w.find('ChartSeriesSelect[column="A"] option').not('.prompt')).toHaveLength(4)
  })
})
