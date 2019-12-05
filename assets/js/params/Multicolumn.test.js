/* globals describe, expect, it, jest */
import React from 'react'
import Multicolumn from './Multicolumn'
import { mountWithI18n } from '../i18n/test-utils.js'

describe('Multicolumn', () => {
  const wrapper = (extraProps = {}) => mountWithI18n(
    <Multicolumn
      onChange={jest.fn()}
      name='columns'
      fieldId='columns'
      isReadOnly={false}
      value={['A', 'C']}
      inputColumns={[{ name: 'A' }, { name: 'B' }, { name: 'C' }, { name: 'D' }]}
      {...extraProps}
    />
  )

  describe('read-only', () => {
    it('renders read-only column names', () => {
      const w = wrapper({
        isReadOnly: true,
        value: ['A', 'C']
      })
      expect(w.find('.react-select__control').text()).toMatch(/A.*C/)
    })
  })

  describe('NOT Read-only', () => {
    it('renders column names', () => {
      const w = wrapper()
      expect(w.find('Select[name="columns"]').prop('options')).toHaveLength(4)
      expect(w.find('Select[name="columns"]').prop('options')).toEqual([{ label: 'A', value: 'A' }, { label: 'B', value: 'B' }, { label: 'C', value: 'C' }, { label: 'D', value: 'D' }])
    })

    it('selects all columns when "select all" is clicked', () => {
      const w = wrapper()
      w.find('.react-select__dropdown-indicator')
        .simulate('mousedown', { type: 'mousedown', button: 0 }) // open menu
      w.find('button.multicolumn-select-all').simulate('click')
      expect(w.prop('onChange')).toHaveBeenCalledWith(['A', 'B', 'C', 'D'])
    })

    it('deselects all columns when "select none" is clicked', () => {
      const w = wrapper()
      w.find('.react-select__dropdown-indicator')
        .simulate('mousedown', { type: 'mousedown', button: 0 }) // open menu
      w.find('button.multicolumn-select-none').simulate('click')
      expect(w.prop('onChange')).toHaveBeenCalledWith([])
    })

    it('renders loading when no columns', () => {
      const w = wrapper({ inputColumns: null })
      expect(w.find('ReactSelect').prop('isLoading')).toBe(true)
    })

    it('should sort the selected columns in order', () => {
      const w = mountWithI18n(
        <Multicolumn
          onChange={jest.fn()}
          name='column'
          fieldId='column'
          isReadOnly={false}
          value={['C', 'A', 'D']}
          inputColumns={[{ name: 'D' }, { name: 'A' }, { name: 'C' }, { name: 'B' }]}
        />
      )
      const expected = [
        { label: 'D', value: 'D' },
        { label: 'A', value: 'A' },
        { label: 'C', value: 'C' }
      ]
      expect(w.find('Select').prop('value')).toEqual(expected)
    })

    it('should call onChange when columns are added', () => {
      const w = wrapper({
        value: ['A'],
        inputColumns: [{ name: 'A' }, { name: 'B' }, { name: 'C' }]
      })
      w.find('.react-select__dropdown-indicator')
        .simulate('mousedown', { type: 'mousedown', button: 0 }) // open menu
      w.find('.react-select__option').at(0).simulate('click')
      expect(w.prop('onChange')).toHaveBeenCalledWith(['A', 'B'])
    })

    it('should handle DEPRECATED values of type String', () => {
      const w = wrapper({
        value: 'A,B',
        inputColumns: [{ name: 'A' }, { name: 'B' }, { name: 'C' }]
      })
      w.find('.react-select__dropdown-indicator')
        .simulate('mousedown', { type: 'mousedown', button: 0 }) // open menu
      w.find('.react-select__option').at(0).simulate('click')
      expect(w.prop('onChange')).toHaveBeenCalledWith('A,B,C')
    })
  })
})
