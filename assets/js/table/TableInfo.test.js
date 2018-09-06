import React from 'react'
import { mount } from 'enzyme'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import TableInfo from './TableInfo'

describe('TableInfo', () => {
  const mockStore = configureStore()

  const wrapper = (extraProps={}) => {
    // mock store for <SelectedRowsActions>, a descendent
    const store = mockStore({ modules: {} })

    return mount(
      <Provider store={store}>
        <TableInfo
          nRows={10}
          nColumns={3}
          isReadOnly={false}
          selectedWfModuleId={99}
          selectedRowIndexes={[]}
          onClickRowsAction={jest.fn()}
          {...extraProps}
        />
      </Provider>
    )
  }

  it('should number-format row and column counts', () => {
    const w = wrapper({ nRows: 2000, nColumns: 3123 })
    const numberFormat = new Intl.NumberFormat()
    expect(w.text()).toContain(numberFormat.format(2000))
    expect(w.text()).toContain(numberFormat.format(3123))
  })
})
