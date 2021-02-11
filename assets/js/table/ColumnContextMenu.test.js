/* global describe, it, jest, expect */
import ColumnContextMenu from './ColumnContextMenu'
import { mountWithI18n } from '../i18n/test-utils'

describe('ColumnContextMenu', () => {
  function mountMenu (onClickAction, columnKey, columnType, renameColumn) {
    return mountWithI18n(
      <ColumnContextMenu
        onClickAction={onClickAction}
        columnKey={columnKey}
        columnType={columnType}
        renameColumn={renameColumn}
      />
    )
  }

  it('should match snapshot', () => {
    const wrapper = mountMenu(jest.fn(), 'columnKey', 'text', jest.fn())
    expect(wrapper).toMatchSnapshot() // stores file which represents tree of component
  })

  // only checking the call to drop down functions, not actual actions on table
  it('should call functions ', async () => {
    const onClickAction = jest.fn()
    const renameColumn = jest.fn()

    const wrapper = mountMenu(onClickAction, 'columnKey', 'text', renameColumn)

    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.drop-column').simulate('click')
    expect(onClickAction).toHaveBeenCalledWith('selectcolumns', false, { keep: false })

    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.rename-column-header').simulate('click')
    expect(renameColumn).toHaveBeenCalled()

    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.duplicatecolumns').simulate('click')
    expect(onClickAction).toHaveBeenCalledWith('duplicatecolumns', false, {})

    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.filter-column').simulate('click')
    expect(onClickAction).toHaveBeenCalledWith('filter', true, {})

    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.sort-ascending').simulate('click')
    expect(onClickAction).toHaveBeenCalledWith('sort', false, { is_ascending: true })

    wrapper.find('button').simulate('click') // open dropdown
    wrapper.find('DropdownItem.sort-descending').simulate('click')
    expect(onClickAction).toHaveBeenCalledWith('sort', false, { is_ascending: false })
  })
})
