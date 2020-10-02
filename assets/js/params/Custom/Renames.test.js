/* globals describe, expect, it, jest */
import React from 'react'
import Renames from './Renames'
import { mount } from 'enzyme'

describe('Renames', () => {
  const testEntries = {
    name: 'host_name',
    narrative: 'nrtv'
  }

  const columnNames = ['name', 'build_year', 'narrative', 'cornerstone']
  const inputColumns = columnNames.map(name => ({ name }))

  const wrapper = (extraProps = {}) => mount(
    <Renames
      inputColumns={inputColumns}
      stepId={1}
      onChange={jest.fn()}
      value={testEntries}
      isReadOnly={false}
      {...extraProps}
    />
  )

  it('displays all columns when initialized empty', () => {
    // This test corresponds to behavior when added from module library.
    const tree = wrapper({ value: {} })

    expect(tree.find('.rename-input')).toHaveLength(4)
    expect(tree.find('.rename-input').get(0).props.value).toEqual('name')
    expect(tree.find('.rename-input').get(1).props.value).toEqual('build_year')
  })

  it('displays only columns in entries', () => {
    const tree = wrapper({ value: testEntries })

    expect(tree.find('.rename-input')).toHaveLength(2)
    expect(tree.find('.rename-input').get(0).props.value).toEqual('host_name')
    expect(tree.find('.rename-input').get(1).props.value).toEqual('nrtv')
  })

  it('updates parameter upon input', () => {
    const tree = wrapper()
    const yearInput = tree.find('input[value="host_name"]')
    yearInput.simulate('change', { target: { value: 'hn' } })
    expect(tree.prop('onChange')).toHaveBeenCalledWith({ name: 'hn', narrative: 'nrtv' })
  })

  it('updates when receiving data from elsewhere', () => {
    // related: https://www.pivotaltracker.com/story/show/160661659
    const tree = wrapper({
      inputColumns: [{ name: 'A' }, { name: 'B' }],
      value: {}
    })

    tree.setProps({ value: { A: 'C' } })
    expect(tree.find('.rename-input').get(0).props.value).toEqual('C')
  })

  it('does not crash when there are no columns', () => {
    // https://www.pivotaltracker.com/story/show/161945886
    const tree = wrapper({ inputColumns: null, value: {} })
    expect(tree.find('.rename-entry')).toHaveLength(0)
  })

  it('updates parameter upon deleting an entry', () => {
    const tree = wrapper()
    tree.find('RenameEntry').first().find('.rename-delete').simulate('click')
    expect(tree.prop('onChange')).toHaveBeenCalledWith({ narrative: 'nrtv' })
  })
})
