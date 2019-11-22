/* globals describe, expect, it, jest */
import React from 'react'
import SortColumns from './index'
import { mountWithI18n } from '../../../i18n/test-utils'

describe('SortColumns', () => {
  const wrapper = (extraProps = {}) => mountWithI18n(
    <SortColumns
      isReadOnly={false}
      name='sort_columns'
      fieldId='sort_columns'
      value={[]}
      inputColumns={[{ name: 'A' }, { name: 'B' }, { name: 'C' }]}
      onChange={jest.fn()}
      {...extraProps}
    />
  )

  it('should only be able to add same number of params as columns', () => {
    const w = wrapper({})

    w.find('button[name="sort_columns[add]"]').simulate('click') // add new param
    expect(w.prop('onChange')).toHaveBeenCalledWith([{ colname: '', is_ascending: true }, { colname: '', is_ascending: true }])
    w.setProps({ value: [{ colname: '', is_ascending: true }, { colname: '', is_ascending: true }] })

    w.find('button[name="sort_columns[add]"]').simulate('click') // add new param
    expect(w.prop('onChange')).toHaveBeenCalledWith([{ colname: '', is_ascending: true },
      { colname: '', is_ascending: true }, { colname: '', is_ascending: true }])
    w.setProps({
      value: [{ colname: '', is_ascending: true },
        { colname: '', is_ascending: true }, { colname: '', is_ascending: true }]
    })

    expect(w.find('button[name="sort_columns[add]"]')).toHaveLength(0)
  })

  it('Should call onChange when params added', () => {
    const w = wrapper({})
    w.find('.react-select__dropdown-indicator').simulate('mousedown', { type: 'mousedown', button: 0 }) // open menu
    w.find('.react-select__option').at(0).simulate('click') // Select column 'A'

    expect(w.prop('onChange')).toHaveBeenCalledWith([{ colname: 'A', is_ascending: true }])
  })

  it('Should remove a value from the list when delete pressed', () => {
    const w = wrapper({}).setProps({ value: [{ colname: 'A', is_ascending: true }, { colname: 'B', is_ascending: true }] })
    w.find('button[name="sort_columns[1][delete]"]').simulate('click') // delete last param
    expect(w.prop('onChange')).toHaveBeenCalledWith([{ colname: 'A', is_ascending: true }])
  })
})
