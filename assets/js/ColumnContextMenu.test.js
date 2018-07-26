/* global describe, it, jest, expect */
import React from 'react'
import ColumnContextMenu from './ColumnContextMenu'
import { shallow } from 'enzyme'
import { sortDirectionNone, sortDirectionAsc, sortDirectionDesc } from './UpdateTableAction'
import { tick } from './test-utils'

describe('ColumnContextMenu', () => {
  function mountMenu (sortDirection, setSortDirection, duplicateColumn, renameColumn, dropColumn, filterColumn) {
    return shallow(
      <ColumnContextMenu
        sortDirection={sortDirection}
        setSortDirection={setSortDirection}
        duplicateColumn={duplicateColumn}
        renameColumn={renameColumn}
        dropColumn={dropColumn}
        filterColumn={filterColumn}
      />
    )
  }

  it('should match snapshot', () => {
    let wrapper = mountMenu(sortDirectionNone, jest.fn(), jest.fn(), jest.fn(), jest.fn(), jest.fn())
    expect(wrapper).toMatchSnapshot() // stores file which represents tree of component
  })

  // only checking the call to drop down functions, not actual actions on table
  it('should call functions ', async () => {
    const setSortDirection = jest.fn()
    const duplicateColumn = jest.fn()
    const dropColumn = jest.fn()
    const renameColumn = jest.fn()
    const filterColumn = jest.fn()

    const wrapper = mountMenu(sortDirectionNone, setSortDirection, duplicateColumn, renameColumn, dropColumn, filterColumn)

    wrapper.find('DropdownItem.drop-column').simulate('click')
    expect(dropColumn).toHaveBeenCalled()

    wrapper.find('DropdownItem.rename-column-header').simulate('click')
    expect(renameColumn).toHaveBeenCalled()

    wrapper.find('DropdownItem.duplicate-column').simulate('click')
    expect(duplicateColumn).toHaveBeenCalled()

    wrapper.find('DropdownItem.filter-column').simulate('click')
    expect(filterColumn).toHaveBeenCalled()

    wrapper.find('DropdownItem.sort-ascending').simulate('click')
    expect(setSortDirection).toHaveBeenCalledWith(sortDirectionAsc)

    wrapper.find('DropdownItem.sort-descending').simulate('click')
    expect(setSortDirection).toHaveBeenCalledWith(sortDirectionDesc)
  })
})
