/* globals describe, expect, it, jest */
import React from 'react'
import ParamsForm from './ParamsForm'
import { shallow } from 'enzyme'

const field = (idName, type, extra = {}) => ({
  idName,
  name: '',
  type: type,
  multiline: false,
  placeholder: '',
  ...extra
})

describe('ParamsForm', () => {
  const wrapper = (extraProps = {}) => shallow(
    <ParamsForm
      isReadOnly={false}
      isZenMode={false}
      api={{ createOauthAccessToken: jest.fn(), valueCounts: jest.fn() }}
      fields={[]}
      files={[]}
      value={{ }}
      edits={{ }}
      workflowId={99}
      wfModuleId={1}
      wfModuleSlug='step-1'
      wfModuleOutputErrors={[]}
      isWfModuleBusy={false}
      inputWfModuleId={null}
      inputDeltaId={null}
      inputColumns={[]}
      tabs={[]}
      currentTab='tab-1'
      applyQuickFix={jest.fn()}
      startCreateSecret={jest.fn()}
      submitSecret={jest.fn()}
      deleteSecret={jest.fn()}
      onChange={jest.fn()}
      onSubmit={jest.fn()}
      {...extraProps}
    />
  )

  describe('value and edits', () => {
    it('should call onChange with new values', () => {
      const w = wrapper({
        fields: [
          field('a', 'string'),
          field('b', 'string'),
          field('c', 'string')
        ],
        value: {
          a: 'A',
          b: 'B',
          c: 'C'
        },
        edits: {
          a: 'x'
        }
      })
      w.find('Param[name="c"]').prop('onChange')('c', 'foo')

      expect(w.instance().props.onChange).toHaveBeenCalledWith({ a: 'x', c: 'foo' })
    })

    it('should delete edits in onChange instead of sending original values', () => {
      // The smaller we keep WfModule.state.edits, the better: that way when
      // a change comes from the server the user will see it because the edits
      // won't overwrite it.
      const w = wrapper({
        fields: [
          field('a', 'string'),
          field('b', 'string')
        ],
        value: {
          a: 'A',
          b: 'B'
        },
        edits: {
          a: 'x',
          b: 'y'
        }
      })
      w.find('Param[name="b"]').prop('onChange')('b', 'B')

      expect(w.instance().props.onChange).toHaveBeenCalledWith({ a: 'x' })
    })

    it('should not call onChange on no-op change', () => {
      const w = wrapper({
        fields: [
          field('a', 'string')
        ],
        value: {
          a: 'A'
        },
        edits: {
          a: 'x'
        }
      })
      w.find('Param[name="a"]').prop('onChange')('a', 'x')

      expect(w.instance().props.onChange).not.toHaveBeenCalled()
    })

    it('should set secretMetadata when the field is of type secret', () => {
      const w = wrapper({
        fields: [
          field('a', 'secret', {
            secret_logic: { provider: 'oauth', service: 'google' }
          })
        ],
        value: {},
        secrets: { a: { name: 'a@example.com' } }
      })
      expect(w.find('Param[name="a"]').prop('secretMetadata')).toEqual({ name: 'a@example.com' })
    })

    it('should set secretMetadata=null when the field of type secret has no value', () => {
      const w = wrapper({
        fields: [
          field('a', 'secret', {
            secret_logic: { provider: 'oauth', service: 'google' }
          })
        ],
        value: {},
        secrets: {}
      })
      expect(w.find('Param[name="a"]').prop('secretMetadata')).toBe(null)
    })

    it('should set secretMetadata when the field has a secretParameter', () => {
      const w = wrapper({
        fields: [
          field('a', 'secret', {
            secret_logic: { provider: 'oauth', service: 'google' }
          }),
          field('b', 'string', { secretParameter: 'a' })
        ],
        value: { b: 'foo' },
        secrets: { a: { name: 'a@example.com' } }
      })
      expect(w.find('Param[name="b"]').prop('secretMetadata')).toEqual({ name: 'a@example.com' })
    })

    it('should set secretMetadata=null when the field has a secretParameter with no secret set', () => {
      const w = wrapper({
        fields: [
          field('a', 'secret', {
            secret_logic: { provider: 'oauth', service: 'google' }
          }),
          field('b', 'string', { secretParameter: 'a' })
        ],
        value: { b: 'foo' },
        secrets: {}
      })
      expect(w.find('Param[name="b"]').prop('secretMetadata')).toBe(null)
    })
  })

  describe('visibleIf', () => {
    it('should show conditional parameter matching menu value', () => {
      const w = wrapper({
        fields: [
          field('menu_select', 'menu', {
            enumOptions: [
              { value: 'mango', label: 'Mango' },
              'separator',
              { value: 'banana', label: 'Banana' }
            ]
          }),
          field('testme', 'string', { visibleIf: { idName: 'menu_select', value: ['banana', 'orange'] } })
        ],
        value: {
          menu_select: 'banana',
          testme: ''
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(1)
    })

    it('should hide conditional parameter not-matching menu value', () => {
      const w = wrapper({
        fields: [
          field('menu_select', 'menu', {
            enumOptions: [
              { value: 'mango', label: 'Mango' },
              'separator',
              { value: 'banana', label: 'Banana' }
            ]
          }),
          field('testme', 'string', { visibleIf: { idName: 'menu_select', value: ['banana', 'orange'] } })
        ],
        value: {
          menu_select: 'mango',
          testme: ''
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(0)
    })

    it('should hide conditional parameter matching inverted menu value', () => {
      const w = wrapper({
        fields: [
          field('menu_select', 'menu', {
            enumOptions: [
              { value: 'mango', label: 'Mango' },
              'separator',
              { value: 'banana', label: 'Banana' }
            ]
          }),
          field('testme', 'string', { visibleIf: { idName: 'menu_select', value: ['banana', 'orange'], invert: true } })
        ],
        value: {
          menu_select: 'banana',
          testme: ''
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(0)
    })

    it('should show conditional parameter that depends on a checkbox', () => {
      const w = wrapper({
        fields: [
          field('show', 'checkbox'),
          field('testme', 'string', { visibleIf: { idName: 'show', value: true } })
        ],
        value: {
          show: true,
          testme: ''
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(1)
    })

    it('should hide conditional parameter that depends on a checkbox', () => {
      const w = wrapper({
        fields: [
          field('show', 'checkbox'),
          field('testme', 'string', { visibleIf: { idName: 'show', value: true } })
        ],
        value: {
          show: false,
          testme: ''
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(0)
    })

    it('should show conditional parameter that depends on an inverted checkbox', () => {
      const w = wrapper({
        fields: [
          field('hide', 'checkbox'),
          field('testme', 'string', { visibleIf: { idName: 'hide', value: true, invert: true } })
        ],
        value: {
          hide: false,
          testme: ''
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(1)
    })

    it('should hide conditional parameter depending on hidden conditional parameter, even when condition is met', () => {
      const w = wrapper({
        fields: [
          field('show1', 'checkbox'),
          field('show2', 'checkbox', { visibleIf: { idName: 'show1', value: true } }),
          field('testme', 'string', { visibleIf: { idName: 'show2', value: true } })
        ],
        value: {
          show1: false, // hides show2
          show2: true, // but it's hidden, so value doesn't matter
          testme: ''
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(0)
    })

    it('should warn and hide on simple recursion', () => {
      jest.spyOn(global.console, 'warn').mockImplementation(() => {})
      const w = wrapper({
        fields: [
          field('x', 'string', { visibleIf: { idName: 'x', value: 'x' } })
        ],
        value: { x: 'x' }
      })
      expect(global.console.warn).toHaveBeenCalled()
      expect(w.find('Param[name="x"]')).toHaveLength(0)
    })

    it('should warn and hide on non-simple recursion', () => {
      jest.spyOn(global.console, 'warn').mockImplementation(() => {})
      const w = wrapper({
        fields: [
          field('x', 'string', { visibleIf: { idName: 'y', value: 'y' } }),
          field('y', 'string', { visibleIf: { idName: 'x', value: 'x' } })
        ],
        value: { x: 'x', y: 'y' }
      })
      expect(global.console.warn).toHaveBeenCalledTimes(2)
      expect(w.find('Param[name="x"]')).toHaveLength(0)
      expect(w.find('Param[name="y"]')).toHaveLength(0)
    })

    it('should deep-compare JSON values', () => {
      const w = wrapper({
        fields: [
          field('boo', 'custom'),
          field('testme', 'statictext', { visibleIf: { idName: 'boo', value: ['x', 'y'] } })
        ],
        value: {
          boo: ['x', 'y'],
          testme: '1,3-9'
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(1)
    })
  })
})
