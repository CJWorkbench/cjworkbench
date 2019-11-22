/* global describe, it, expect, jest */
import React from 'react'
import RefineBins from './RefineBins'
import { mountWithI18n } from '../../../i18n/test-utils.js'

describe('RefineBins', () => {
  const testBins = [
    { name: 'a', isSelected: true, count: 3, bucket: { a: 2, b: 3 } },
    { name: 'x', isSelected: false, count: 2, bucket: { x: 1, y: 1 } }
  ]

  const wrapper = (extraProps = {}) => mountWithI18n(
    <RefineBins
      bins={testBins}
      onChange={jest.fn()}
      {...extraProps}
    />
  )

  it('should render a message when there are no bins', () => {
    const w = wrapper({ bins: [] })
    expect(w.find('.no-bins Trans[id="js.params.Custom.RefineBins.noClustersFound"]')).toHaveLength(1)
    expect(w.find('table')).toHaveLength(0)
  })

  it('should render checkboxes for isSelected', () => {
    const w = wrapper()
    expect(w.find('input[type="checkbox"]').at(0).prop('checked')).toBe(true)
    expect(w.find('input[type="checkbox"]').at(1).prop('checked')).toBe(false)
  })

  it('should change isSelected', () => {
    const w = wrapper()
    w.find('input[type="checkbox"]').at(1).simulate('change', { target: { checked: true } })
    expect(w.prop('onChange')).toHaveBeenCalledWith([
      testBins[0],
      { ...testBins[1], isSelected: true }
    ])
  })

  it('should render names', () => {
    const w = wrapper()
    expect(w.find('textarea').at(0).text()).toEqual('a')
    expect(w.find('textarea').at(1).text()).toEqual('x')
  })

  it('should change name', () => {
    const w = wrapper()
    w.find('textarea').at(0).simulate('change', { target: { value: 'A' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith([
      { ...testBins[0], name: 'A' },
      testBins[1]
    ])
  })

  it('should sort values within a bucket by count', () => {
    const w = wrapper()
    expect(w.find('td.value').at(0).text()).toEqual('b')
    expect(w.find('td.value').at(1).text()).toEqual('a')
  })

  it('should sort values within a bucket by name when count is equal', () => {
    const w = wrapper()
    expect(w.find('td.value').at(2).text()).toEqual('x')
    expect(w.find('td.value').at(3).text()).toEqual('y')
  })
})
