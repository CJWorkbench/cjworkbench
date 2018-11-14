import React from 'react'
import RenameEntries, {RenameEntry} from './RenameEntries'
import {mount} from 'enzyme'
import {jsonResponseMock} from '../test-utils'

jest.mock('../workflow-reducer')
import { store, deleteModuleAction } from '../workflow-reducer'

describe('RenameEntries rendering and interactions', () => {
  const testEntries = {
    'name': 'host_name',
    'narrative': 'nrtv'
  }

  const columnNames = ['name', 'build_year', 'narrative', 'cornerstone']
  const allColumns = columnNames.map(name => ({ name }))

  const WFM_ID = 1

  const wrapper = (extraProps={}) => mount(
    <RenameEntries
      allColumns={allColumns}
      wfModuleId={WFM_ID}
      onChange={jest.fn()}
      entriesJsonString={JSON.stringify(testEntries)}
      isReadOnly={false}
      {...extraProps}
    />
  )

  it('displays all columns when initialized empty', () => {
    // This test corresponds to behavior when added from module library.
    const tree = wrapper({ entriesJsonString: '' })

    expect(tree.find('.rename-input')).toHaveLength(4)
    expect(tree.find('.rename-input').get(0).props.value).toEqual('name')
    expect(tree.find('.rename-input').get(1).props.value).toEqual('build_year')
  })

  it('displays only columns in entries', () => {
    const tree = wrapper({ entriesJsonString: JSON.stringify(testEntries) })

    expect(tree.find('.rename-input')).toHaveLength(2)
    expect(tree.find('.rename-input').get(0).props.value).toEqual('host_name')
    expect(tree.find('.rename-input').get(1).props.value).toEqual('nrtv')
  })

  it('updates parameter upon input completion via blur', () => {
    const tree = wrapper()

    const yearInput = tree.find('input[value="host_name"]')
    yearInput.simulate('change', { target: { value: 'hn' } })
    yearInput.simulate('blur')

    expect(tree.prop('onChange')).toHaveBeenCalled()
    const calls = tree.prop('onChange').mock.calls
    expect(JSON.parse(calls[0][0])).toEqual({
      name: 'hn',
      narrative: 'nrtv'
    })
  })

  it('updates parameter upon input completion via enter key', () => {
    const tree = wrapper()

    const yearInput = tree.find('input[value="host_name"]')
    yearInput.simulate('change', { target: { value: 'hn' } })
    yearInput.simulate('keypress', { key: 'Enter' })

    expect(tree.prop('onChange')).toHaveBeenCalled()
    const calls = tree.prop('onChange').mock.calls
    expect(JSON.parse(calls[0][0])).toEqual({
      name: 'hn',
      narrative: 'nrtv'
    })
  })

  it('updates when receiving data from elsewhere', () => {
    // related: https://www.pivotaltracker.com/story/show/160661659
    const tree = wrapper({
      allColumns: [{name: 'A'}, {name: 'B'}],
      entriesJsonString: '{}'
    })

    tree.setProps({ entriesJsonString: '{"A":"C"}' })
    expect(tree.find('.rename-input').get(0).props.value).toEqual('C')
  })

  it('does not crash when there are no columns', () => {
    // https://www.pivotaltracker.com/story/show/161945886
    const tree = wrapper({ allColumns: null, entriesJsonString: '' })
    expect(tree.find('.rename-entry')).toHaveLength(0)
  })

  it('updates parameter upon deleting an entry', () => {
    const tree = wrapper()
    tree.find('RenameEntry').first().find('.rename-delete').simulate('click')
    expect(tree.prop('onChange')).toHaveBeenCalledWith(JSON.stringify({ narrative: 'nrtv' }))
  })

  it('deletes itself if all entries are deleted', () => {
    // TODO just use a func prop, not Redux
    const state = {
      workflow: {
        wf_modules: [
          {
            id: WFM_ID - 1
          },
          {
            id: WFM_ID
          }
        ]
      }
    }
    store.getState.mockImplementation(() => state)
    deleteModuleAction.mockImplementation((...args) => [ 'deleteModuleAction', ...args ])

    const tree = wrapper({ entriesJsonString: JSON.stringify({ 'name': 'n' }) })
    tree.find('RenameEntry .rename-delete').simulate('click')
    expect(store.dispatch).toHaveBeenCalledWith([ 'deleteModuleAction', WFM_ID ])
  })
})
