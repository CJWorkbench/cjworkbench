/* globals describe, expect, it, jest */
import React from 'react'
import ConnectedImportModuleFromGitHub from './ImportModuleFromGitHub'
import { mountWithI18n } from './i18n/test-utils'
import { Provider } from 'react-redux'
import { mockStore, tick } from './test-utils'

describe('ImportModuleFromGitHub', () => {
  const wrapper = (store, extraProps = {}) => {
    return mountWithI18n(
      <Provider store={store}>
        <ConnectedImportModuleFromGitHub
          closeModal={jest.fn()}
          api={{ importModuleFromGitHub: () => {} }}
          {...extraProps}
        />
      </Provider>
    )
  }

  it('should load and replace a module', async () => {
    const api = {
      importModuleFromGitHub: jest.fn().mockImplementation(() => Promise.resolve({
        id_name: 'b',
        author: 'Aut',
        name: 'yay',
        category: 'cat'
      }))
    }
    const store = mockStore({
      modules: {
        a: { foo: 'bar' }
      },
      loggedInUser: { is_staff: true }
    }, null)
    const w = wrapper(store, { api })
    w.find('input').instance().value = 'https://github.com/example/repo'
    w.find('form').simulate('submit')

    expect(api.importModuleFromGitHub).toHaveBeenCalledWith('https://github.com/example/repo')
    await tick()
    expect(store.getState().modules).toEqual({
      a: { foo: 'bar' },
      b: { id_name: 'b', author: 'Aut', category: 'cat', name: 'yay' }
    })

    expect(w.find('.import-github-success').text()).toEqual('Imported module {module} under category {category}')
  })

  it('should display a link but no form for non-staff users', () => {
    const api = { importModuleFromGitHub: jest.fn() }
    const store = mockStore({
      modules: {},
      loggedInUser: { is_staff: false }
    }, null)
    const w = wrapper(store, { api })
    expect(w.find('input')).toHaveLength(0)
    expect(w.find('Trans[defaults*="<0>here</0>"]')).toHaveLength(1) // external link => to docs
  })
})
