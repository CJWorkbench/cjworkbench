/* globals describe, expect, it, jest */
import React from 'react'
import List from './List'
import { mountWithI18n } from '../i18n/test-utils.js'

describe('List', () => {
  it('should change when sub-params change', () => {
    /*
     * This is a bit of an integration test. Here's why:
     *
     * [2019-04-18] we had three different concepts on each component:
     *
     * * `fieldId` HTML `id`. It's got to be unique for each field.
     * * `name` HTML `name`, used in unit tests. It's meant to be unique so
     *   unit tests can use it.
     * * `idName` the _param name_. It's the nested name.
     *
     * ... but as of [2019-04-18] we only had two props. So something had to
     * fall by the wayside. Today, it's `name`.
     *
     * TODO build all three props, or change all tests to use `fieldId`.
     * In other words: put a bit more tought into this.
     *
     * In the meantime, this test (with an id, since `name` is a gray area)
     * should prevent us from regressing and trying to fix the `name` while
     * we still depend on it in event handlers.
     */
    const w = mountWithI18n(
      <List
        isReadOnly={false}
        label='List'
        fieldId='list'
        name='list'
        onChange={jest.fn()}
        onSubmit={jest.fn()}
        childParameters={[
          {
            idName: 'x',
            type: 'string',
            name: 'X', // html name
            placeholder: ''
          }
        ]}
        childDefault={{ x: '' }}
        value={[{ x: 'foo' }, { x: 'bar' }]}
        upstreamValue={[{ x: 'foo' }, { x: 'bar' }]}
        // The rest are props we just can't avoid....
        applyQuickFix={jest.fn()}
        startCreateSecret={jest.fn()}
        deleteSecret={jest.fn()}
        currentTab=''
        tabs={[]}
        isWfModuleBusy={false}
        isZenMode={false}
        onDelete={jest.fn()}
      />
    )

    const el = w.find('#list_1_x')
    el.simulate('change', { target: { name: el.prop('name'), value: 'baz' } })
    expect(w.prop('onChange')).toHaveBeenCalledWith([{ x: 'foo' }, { x: 'baz' }])
  })
})
