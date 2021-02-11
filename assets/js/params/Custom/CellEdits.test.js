/* globals describe, expect, it */
import CellEdits from './CellEdits'
import { mount } from 'enzyme'

describe('CellEdits', () => {
  it('renders correctly', () => {
    const wrapper = mount(
      <CellEdits
        value={[
          { row: 3, col: 'foo', value: 'bar' },
          { row: 6, col: 'food', value: 'sandwich' },
          { row: 5, col: 'foo', value: 'gak' },
          { row: 17, col: 'food', value: 'pizza' }
        ]}
      />
    )

    expect(wrapper.find('.cell-edits--column')).toHaveLength(2)
    expect(wrapper.find('.cell-edits--row')).toHaveLength(4)

    expect(wrapper).toMatchSnapshot()
  })

  it('renders empty data', () => {
    const wrapper = mount(
      <CellEdits value={[]} />
    )

    expect(wrapper.find('.cell-edits--column')).toHaveLength(0)
    expect(wrapper.find('.cell-edits--row')).toHaveLength(0)

    expect(wrapper).toMatchSnapshot()
  })
})
