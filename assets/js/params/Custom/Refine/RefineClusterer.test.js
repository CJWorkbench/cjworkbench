/* global describe, it, expect, jest */
import React from 'react'
import { mountWithI18n } from '../../../i18n/test-utils.js'
import { tick } from '../../../test-utils'
import RefineClusterer from './RefineClusterer'

describe('RefineClusterer', () => {
  const wrapper = (extraProps = {}) => mountWithI18n(
    <RefineClusterer
      bucket={{ a: 1, b: 1, aaaaa: 2 }}
      onProgress={jest.fn()}
      onComplete={jest.fn()}
      {...extraProps}
    />
  )

  it('should default to "fingerprint" algorithm', () => {
    const w = wrapper()
    expect(w.find('select').prop('value')).toEqual('fingerprint')
  })

  it('should run the algorithm on start', async () => {
    const w = wrapper()
    await tick() // let the algorithm run and let its complete handler run
    expect(w.prop('onComplete')).toHaveBeenCalledWith([])
  })

  it('should cancel the algorithm and start the new one when selecting', async () => {
    const w = wrapper()
    w.find('select').simulate('change', { target: { value: 'levenshtein' } })
    await tick() // let the algorithm run and let its complete handler run
    expect(w.prop('onComplete')).not.toHaveBeenCalledWith([])
    expect(w.prop('onComplete')).toHaveBeenCalledWith([
      {
        name: 'a',
        count: 2,
        bucket: { a: 1, b: 1 }
      }
    ])
  })

  it('sort elements by count before clustering', async () => {
    // JS Object elements are ordered  in insertion order
    const w = wrapper({ bucket: { x: 1, yy: 1, xxx: 2 } })
    w.find('select').simulate('change', { target: { value: 'levenshtein' } })
    w.find('input#refine-clusterer-max-distance').simulate(
      'change',
      { target: { name: 'maxDistance', value: '2' } }
    )
    await tick() // let the algorithm run and let its complete handler run
    expect(w.prop('onComplete')).toHaveBeenCalledWith([
      {
        name: 'xxx',
        count: 3,
        bucket: { xxx: 2, x: 1 } // _not_ { x: 1, yy: 1, xxx: 2 } -- we should choose xxx as center
      }
    ])
  })

  it('should render and handle levenshtein options', async () => {
    const w = wrapper()
    w.find('select').simulate('change', { target: { value: 'levenshtein' } })
    w.update()
    w.find('input[name="maxDistance"]').simulate('change', { target: { name: 'maxDistance', value: '6' } })
    await tick() // let the algorithm run and let its complete handler run
    expect(w.prop('onComplete')).toHaveBeenCalledWith([
      {
        name: 'aaaaa',
        count: 4,
        bucket: { a: 1, b: 1, aaaaa: 2 }
      }
    ])
  })

  it('should report progress', async () => {
    const w = wrapper()
    await tick() // let the algorithm run and let its complete handler run
    expect(w.prop('onProgress')).toHaveBeenCalledWith(0)
  })
})
