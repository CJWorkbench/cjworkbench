import React from 'react'
import ConnectedImportModuleFromGitHub  from './ImportModuleFromGitHub'
import { mount } from 'enzyme'
import { mockStore, tick } from './test-utils'

describe('ImportModuleFromGitHub', () => {
  const wrapper = (store, extraProps={}) => {
    return mount(
      <ConnectedImportModuleFromGitHub
        store={store}
        closeModal={jest.fn()}
        api={{importModuleFromGitHub: () => {}}}
        {...extraProps}
      />
    )
  }

  it('should load and replace a module', async () => {
    const api = {
      importModuleFromGitHub: jest.fn().mockImplementation(() => Promise.resolve({ id: 2, author: 'Aut', name: 'yay', category: 'cat' }))
    }
    const store = mockStore({ modules: {1: {foo: 'bar'}} }, null)
    const w = wrapper(store, { api })
    w.find('input').instance().value = 'https://github.com/example/repo'
    w.find('form').simulate('submit')

    expect(api.importModuleFromGitHub).toHaveBeenCalledWith('https://github.com/example/repo')
    await tick()
    expect(store.getState().modules).toEqual({
      1: { foo: 'bar' },
      2: { id: 2, author: 'Aut', category: 'cat', name: 'yay' }
    })

    expect(w.find('.import-github-success').text()).toEqual('Imported Aut module "yay" under category "cat"')
  })
})
