import React from 'react'
import ColumnContextMenu  from './ColumnContextMenu'
import { mount } from 'enzyme'
import { sortDirectionNone, sortDirectionAsc, sortDirectionDesc } from './SortFromTable'
import { tick } from './test-utils'

describe('ColumnContextMenu', () => {

  const sortDirectionArray = [sortDirectionNone, sortDirectionAsc, sortDirectionDesc]
  let classNameMap = { }
  var sortDirection // global variable used for iterations

  // Can't initialize with JSON because numeric keys.
  classNameMap[sortDirectionAsc] = 'test-sort-ascending'
  classNameMap[sortDirectionDesc] = 'test-sort-descending'

  function mountMenu(sortDirection, setSortDirection) {
    return mount(
      <ColumnContextMenu
        sortDirection={sortDirection}
        setSortDirection={setSortDirection}
      />
    )
  }

  it('should match snapshot', () => {
    let wrapper = mountMenu(sortDirectionNone, jest.fn())
    expect(wrapper).toMatchSnapshot() //stores file which represents tree of component
    })
    //NO MORE CHECK ICON -- PIERRE
  // it('should have check icon: ' + classNameMap[sortDirection], () => {
  //   for (let sortDirectionToCheck of sortDirectionArray) {
  //     let wrapper = mountMenu(sortDirectionToCheck, jest.fn())
  //
  //     let dropDownItem = wrapper.find('DropdownItem.' + classNameMap[sortDirectionToCheck] + '.icon-sort-up')
  //     for (let s of sortDirectionArray) {
  //       s === sortDirection
  //         ? expect(dropDownItem).toHaveLength(1) : expect(dropDownItem).toHaveLength(0)
  //     }
  //   }
  })

  // only checking the call to set the sort direction, not the actual sort
  it('should call setSortDirection', async () => {
    for (let sortDirectionToCheck of sortDirectionArray) {
      let setSortDirection = jest.fn()
      let wrapper = mountMenu(sortDirectionNone, setSortDirection)
      await tick()

      const dropDownItem = wrapper.find('DropdownItem.' + classNameMap[sortDirectionToCheck])
      dropDownItem.simulate('click')
      expect(setSortDirection).toHaveBeenCalledWith(sortDirectionToCheck)
    }
  })

})
