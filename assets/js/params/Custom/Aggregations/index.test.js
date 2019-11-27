/* globals describe, expect, it, jest */
import React from 'react'
import Aggregations from './index'
import { mountWithI18n } from '../../../i18n/test-utils'

describe('Aggregations', () => {
  const wrapper = (extraProps = {}) => mountWithI18n(
    <Aggregations
      isReadOnly={false}
      name='aggregations'
      fieldId='aggregations'
      value={[]}
      allColumns={[{ name: 'A' }, { name: 'B' }, { name: 'C' }]}
      onChange={jest.fn()}
      {...extraProps}
    />
  )

  it('should show "size" when value=[], because groupby.py does', () => {
    const w = wrapper({ aggregations: [] })
    expect(w.find('select[name="aggregations[0][operation]"]').prop('value')).toEqual('size')
  })

  it('should add a "sum" operation when adding over value=[] (which implies "size")', () => {
    const w = wrapper({ aggregations: [] })
    w.find('button[name="aggregations[add]"]').simulate('click')
    expect(w.prop('onChange')).toHaveBeenCalledWith([
      { operation: 'size', colname: '', outname: '' },
      { operation: 'sum', colname: '', outname: '' }
    ])
  })
})
