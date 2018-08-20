import React from 'react'
import ColumnSelector from './ColumnSelector'
import { mount } from 'enzyme'

describe('ColumnSelector', () => {
  const wrapper = (extraProps={}) => mount(
    <ColumnSelector
      name='column'
      isReadOnly={false}
      value='A,C'
      allColumns={[{name: 'A'}, {name: 'B'}, {name: 'C'}, {name: 'D'}]}
      onChange={jest.fn()}
      {...extraProps}
    />
  )

  describe('read-only', () => {
    it('renders read-only column names', () => {
      const w = wrapper({ isReadOnly: true })
      expect(w.find('input[type="checkbox"]')).toHaveLength(4)
      expect(w.find('input[type="checkbox"][readOnly]')).toHaveLength(4)
    })
  })

  describe('NOT Read-only', () => {
    it('renders column names', () => {
      const w = wrapper()
      expect(w.find('input[type="checkbox"]')).toHaveLength(4)
      expect(w.find('label').map(x => x.text())).toEqual(['A', 'B', 'C', 'D'])
    })

    it('deselects column on click', () => {
      const w = wrapper()
      w.find('input[name="column[A]"]').simulate('change', { target: { checked: false, value: 'A'} })
      expect(w.prop('onChange')).toHaveBeenCalledWith('C')
    })

    it('selects column on click', () => {
      const w = wrapper()
      w.find('input[name="column[D]"]').simulate('change', { target: { checked: true, value: 'D'} })
      expect(w.prop('onChange')).toHaveBeenCalledWith('A,C,D')
    })

    it('selects all columns when "select all" is clicked', () => {
      const w = wrapper()
      w.find('button[name="column-select-all"]').simulate('click')
      expect(w.prop('onChange')).toHaveBeenCalledWith('A,B,C,D')
    })

    it('deselects all columns when "select none" is clicked', () => {
      const w = wrapper()
      w.find('button[name="column-select-none"]').simulate('click')
      expect(w.prop('onChange')).toHaveBeenCalledWith('')
    })

    it('renders empty when no columns', () => {
      const w = wrapper({ allColumns: null })
      expect(w.find('.loading')).toHaveLength(1)
    })
  })
})
