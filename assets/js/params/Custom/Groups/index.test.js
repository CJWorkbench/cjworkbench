/* globals describe, expect, it, jest */
import React from 'react'
import Groups from './index'
// import { mount } from 'enzyme'
import { mountWithI18n } from '../../../i18n/test-utils.js'

describe('Groups', () => {
  const wrapper = (extraProps = {}) => mountWithI18n(
    <Groups
      isReadOnly={false}
      name='groups'
      fieldId='groups'
      value={{ colnames: [], group_dates: false, date_granularities: {} }}
      inputColumns={[{ name: 'A', type: 'text' }, { name: 'B', type: 'datetime' }]}
      onChange={jest.fn()}
      applyQuickFix={jest.fn()}
      {...extraProps}
    />
  )

  it('should show pseudo-quick-fix when group_dates:true and there are no date columns', () => {
    const w = wrapper({
      name: 'w',
      value: { colnames: [], group_dates: true, date_granularities: {} },
      inputColumns: [{ name: 'A', type: 'text' }]
    })

    w.find('button[name="w[date_granularities][add-module]"]').simulate('click')
    expect(w.prop('applyQuickFix')).toHaveBeenCalledWith({ type: 'prependStep', moduleSlug: 'convert-date', partialParams: {} })
  })

  it('should show message when group_dates:true and there are unselected date columns', () => {
    const w = wrapper({
      name: 'w',
      value: { colnames: ['A'], group_dates: true, date_granularities: {} },
      inputColumns: [{ name: 'A', type: 'text' }, { name: 'B', type: 'datetime' }]
    })

    expect(w.find('.no-date-selected')).toHaveLength(1)
    expect(w.find('button[name="w[date_granularities][add-module]"]')).toHaveLength(0)
  })

  it('should show dropdown only for selected dates', () => {
    const w = wrapper({
      name: 'w',
      value: { colnames: ['A'], group_dates: true, date_granularities: { A: 'H', B: 'H' } },
      inputColumns: [{ name: 'A', type: 'datetime' }, { name: 'B', type: 'datetime' }]
    })

    expect(w.find('.no-date-selected')).toHaveLength(0)
    expect(w.find('select[name="w[date_granularities][A]"]')).toHaveLength(1)
    expect(w.find('select[name="w[date_granularities][B]"]')).toHaveLength(0)
  })

  it('should set date granularity when there is no value', () => {
    const w = wrapper({
      name: 'w',
      value: { colnames: ['A'], group_dates: true, date_granularities: {} },
      inputColumns: [{ name: 'A', type: 'datetime' }, { name: 'B', type: 'text' }]
    })

    w.find('select[name="w[date_granularities][A]"]').simulate('change', { target: { value: 'H' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith({ colnames: ['A'], group_dates: true, date_granularities: { A: 'H' } })
  })

  it('should show current date granularity', () => {
    const w = wrapper({
      name: 'w',
      value: { colnames: ['A'], group_dates: true, date_granularities: { A: 'H' } },
      inputColumns: [{ name: 'A', type: 'datetime' }, { name: 'B', type: 'text' }]
    })

    expect(w.find('select[name="w[date_granularities][A]"]').prop('value')).toEqual('H')
  })
})
