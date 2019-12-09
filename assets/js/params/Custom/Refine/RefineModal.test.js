/* global describe, it, expect, jest */
import React from 'react'
import { tick } from '../../../test-utils'
import RefineModal from './RefineModal'
import { mountWithI18n } from '../../../i18n/test-utils.js'

describe('RefineModal', () => {
  // These are kinda integration-test-y. See RefineClusterer.test.js and
  // RefineBins.test.js for unit tests.

  const wrapper = (extraProps = {}) => mountWithI18n(
    <RefineModal
      bucket={{ a: 1, b: 1 }}
      onClose={jest.fn()}
      onSubmit={jest.fn()}
      {...extraProps}
    />
  )

  it('should render "fingerprint"-algorithm progressbar on start', () => {
    const w = wrapper()
    // RefineClusterer starts correctly
    expect(w.find('select[name="algorithm"]').prop('value')).toEqual('fingerprint')
    // RefineBins isn't rendered at all
    expect(w.find('table')).toHaveLength(0)
    expect(w.find('.no-bins')).toHaveLength(0)
    // Progressbar is rendered
    expect(w.find('progress')).toHaveLength(1)
  })

  it('should render no bins when there are none', async () => {
    const w = wrapper({ bucket: { a: 1, b: 1 } }) // no bins, with fingerprint
    await tick() // finish clustering
    w.update()
    // RefineBins renders .no-bins
    expect(w.find('table')).toHaveLength(0)
    expect(w.find('.no-bins')).toHaveLength(1)
    // Progressbar isn't rendered
    expect(w.find('progress')).toHaveLength(0)
  })

  it('should render bins when they are found', async () => {
    const w = wrapper({ bucket: { a: 1, 'a ': 1 } }) // one bin, with fingerprint
    await tick() // finish clustering
    w.update()
    // RefineBins renders .no-bins
    expect(w.find('table')).toHaveLength(1)
    expect(w.find('td.value').at(0).text()).toEqual('a')
    // Progressbar isn't rendered
    expect(w.find('progress')).toHaveLength(0)
  })

  it('should submit renames with user-edited name', async () => {
    const w = wrapper({ bucket: { a: 1, 'a ': 1 } }) // one bin, with fingerprint
    await tick() // finish clustering
    w.update()
    w.find('textarea').simulate('change', { target: { value: 'x' } })
    w.update()
    w.find('button[name="submit"]').simulate('click')
    expect(w.prop('onSubmit')).toHaveBeenCalledWith({ a: 'x', 'a ': 'x' })
  })
})
