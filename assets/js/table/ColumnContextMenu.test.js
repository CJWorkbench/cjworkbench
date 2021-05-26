/* global describe, it, jest, expect */
import ColumnContextMenu from './ColumnContextMenu'
import { mountWithI18n } from '../i18n/test-utils'

describe('ColumnContextMenu', () => {
  function mountMenu (onClickAction, columnKey, columnType) {
    return mountWithI18n(
      <ColumnContextMenu
        onClickAction={onClickAction}
        columnKey={columnKey}
        columnType={columnType}
      />
    )
  }

  it('should match snapshot', () => {
    const wrapper = mountMenu(jest.fn(), 'columnKey', 'text', jest.fn())
    expect(wrapper).toMatchSnapshot() // stores file which represents tree of component
  })

  it('should drop a column', () => {
    const call = jest.fn()
    const wrapper = mountMenu(call, 'A', 'text')
    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.drop-column').simulate('click')
    expect(call).toHaveBeenCalledWith('selectcolumns', false, { keep: false })
  })

  it('should duplicate a column', () => {
    const call = jest.fn()
    const wrapper = mountMenu(call, 'A', 'text')
    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.duplicatecolumns').simulate('click')
    expect(call).toHaveBeenCalledWith('duplicatecolumns', false, {})
  })

  it('should filter a column', () => {
    const call = jest.fn()
    const wrapper = mountMenu(call, 'A', 'text')
    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.filter-column').simulate('click')
    expect(call).toHaveBeenCalledWith('filter', true, {})
  })

  it('should sort a column', () => {
    const call = jest.fn()
    const wrapper = mountMenu(call, 'A', 'text')
    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.sort-ascending').simulate('click')
    expect(call).toHaveBeenCalledWith('sort', false, { is_ascending: true })
  })

  it('should sort a column in descending order', () => {
    const call = jest.fn()
    const wrapper = mountMenu(call, 'A', 'text')
    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.sort-descending').simulate('click')
    expect(call).toHaveBeenCalledWith('sort', false, { is_ascending: false })
  })
})
