/* global describe, it, jest, expect */
import React from 'react'
import ColumnContextMenu from './ColumnContextMenu'
import { shallow } from 'enzyme'
import { sortDirectionNone, sortDirectionAsc, sortDirectionDesc } from './UpdateTableAction'

describe('ColumnContextMenu', () => {
  function mountMenu (setDropdownAction, columnKey, columnType, sortDirection, renameColumn) {
    return shallow(
      <ColumnContextMenu
        setDropdownAction={setDropdownAction}
        columnKey={columnKey}
        columnType={columnType}
        sortDirection={sortDirection}
        renameColumn={renameColumn}
      />
    )
  }

  it('should match snapshot', () => {
    let wrapper = mountMenu(jest.fn(), 'columnKey', 'text', sortDirectionNone, jest.fn())
    expect(wrapper).toMatchSnapshot() // stores file which represents tree of component
  })

  // only checking the call to drop down functions, not actual actions on table
  it('should call functions ', async () => {
    const setDropdownAction = jest.fn()
    const renameColumn = jest.fn()

    const wrapper = mountMenu(setDropdownAction, 'columnKey', 'text', sortDirectionNone, renameColumn)

    wrapper.find('DropdownItem.drop-column').simulate('click')
    expect(setDropdownAction).toHaveBeenCalledWith('selectcolumns', false, {})

    wrapper.find('DropdownItem.rename-column-header').simulate('click')
    expect(renameColumn).toHaveBeenCalled()

    wrapper.find('DropdownItem.duplicate-column').simulate('click')
    expect(setDropdownAction).toHaveBeenCalledWith('duplicate-column', false, {})

    wrapper.find('DropdownItem.filter-column').simulate('click')
    expect(setDropdownAction).toHaveBeenCalledWith('filter', true, {})

    wrapper.find('DropdownItem.sort-ascending').simulate('click')
    expect(setDropdownAction).toHaveBeenCalledWith('sort-from-table', false, {sortType: 'text', sortDirection: sortDirectionAsc})

    wrapper.find('DropdownItem.sort-descending').simulate('click')
    expect(setDropdownAction).toHaveBeenCalledWith('sort-from-table', false, {sortType: 'text', sortDirection: sortDirectionDesc})
  })
})
