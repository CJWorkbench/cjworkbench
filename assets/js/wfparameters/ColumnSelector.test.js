import React from 'react'
import ColumnSelector from './ColumnSelector'
import { mount } from 'enzyme'

describe('ColumnSelector', () => {
  const wrapper = (extraProps={}) => mount(
    <ColumnSelector
      onChange={jest.fn()}
      onSubmit={jest.fn()}
      name='column'
      isReadOnly={false}
      initialValue={'A,C'}
      value='A,C'
      allColumns={[{name: 'A'}, {name: 'B'}, {name: 'C'}, {name: 'D'}]}
      {...extraProps}
    />
  )

  describe('read-only', () => {
    it('renders read-only column names', () => {
      const w = wrapper({ isReadOnly: true })
      expect(w.find('Select[name="columns"]').prop('options')).toHaveLength(4)
    })
  })

  describe('NOT Read-only', () => {
    it('renders column names', () => {
      const w = wrapper()
      expect(w.find('Select[name="columns"]').prop('options')).toHaveLength(4)
      expect(w.find('Select[name="columns"]').prop('options')).toEqual([{
        "label": "A", "value": "A"}, {"label": "B", "value": "B"}, {"label": "C", "value": "C"}, {"label": "D", "value": "D"
      }])
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

    it('should sort the selected columns in order', () => {
      const w = mount(
        <ColumnSelector
          name='column'
          isReadOnly={false}
          value='C,A,D'
          allColumns={[{name: 'D'}, {name: 'A'}, {name: 'C'}, {name: 'B'}]}
          onChange={jest.fn()}
        />
      )
      const expected = [
        {label: 'D', value: 'D'},
        {label: 'A', value: 'A'},
        {label: 'C', value: 'C'}
      ]
      expect(w.find('Select[name="columns"]').prop('value')).toEqual(expected)
    })

    it('should not show a submit button when value is unchanged', () => {
      const w = wrapper()
      expect(w.find('button.submit')).toHaveLength(0)
    })

    it('should show submit button when new column added', () => {
      const w = mount(
        <ColumnSelector
          initialValue={'A,B,C'}
          value='A,C'
          allColumns={[{name: 'D'}, {name: 'A'}, {name: 'C'}, {name: 'B'}]}
        />
      )
      expect(w.find('button[title="submit"]')).toHaveLength(1)
    })

    it('should call onChange but not onSubmit when columns are added', () => {
      const w = wrapper()
      w.find('button[title="Select All"]').simulate('click')
      expect(w.prop('onChange')).toHaveBeenCalledWith('A,B,C,D')
      expect(w.prop('onSubmit')).not.toHaveBeenCalled()
    })

    it('should call onSubmit when columns added and button pressed', () => {
      const w = mount(
        <ColumnSelector
          initialValue={'A,B,C'}
          value='A,C'
          allColumns={[{name: 'D'}, {name: 'A'}, {name: 'C'}, {name: 'B'}]}
          onChange={jest.fn()}
          onSubmit={jest.fn()}
        />
      )
      w.find('button[title="submit"]').simulate('click')
      expect(w.prop('onChange')).not.toHaveBeenCalled()
      expect(w.prop('onSubmit')).toHaveBeenCalled()
    })
  })
})
