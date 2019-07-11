/* globals describe, expect, it, jest */
import React from 'react'
import { shallow, mount } from 'enzyme'
import { mockStore, tick } from './test-utils'
import { Provider } from 'react-redux'
import ConnectedEditableWorkflowName, { EditableWorkflowName } from './EditableWorkflowName'

describe('EditableWorkflowName', () => {
  const wrapper = (extraProps = {}) => {
    return shallow(
      <EditableWorkflowName
        value='A'
        setWorkflowName={jest.fn()}
        isReadOnly={false}
        {...extraProps}
      />
    )
  }

  it('renders a plain title when read-only', () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('input')).toHaveLength(0)
  })

  it('lets the user edit the title', () => {
    const setWorkflowName = jest.fn()
    const w = wrapper({ setWorkflowName })
    w.find('input').simulate('change', { target: { value: 'B' } })
    w.find('input').simulate('blur')
    expect(setWorkflowName).toHaveBeenCalledWith('B')
  })

  it('connects to the store', async () => {
    const api = {
      setWorkflowName: jest.fn().mockImplementation(() => Promise.resolve(null))
    }
    const store = mockStore({ workflow: { name: 'A' } }, api)
    const w = mount(
      <Provider store={store}>
        <ConnectedEditableWorkflowName isReadOnly={false} />
      </Provider>
    )
    expect(w.find('input').prop('value')).toEqual('A')
    w.find('input').simulate('change', { target: { value: 'B' } })
    w.find('input').simulate('blur')
    expect(api.setWorkflowName).toHaveBeenCalledWith('B')
    await tick()
    expect(store.getState().workflow.name).toEqual('B')
  })
})
