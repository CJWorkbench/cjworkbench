import React from 'react'
import ParamsForm from './ParamsForm'
import Param from './Param'
import { shallow } from 'enzyme'

const field = (idName, type, extra={}) => ({
  idName,
  name: '',
  type: type,
  multiline: false,
  placeholder: '',
  ...extra
})

describe('ParamsForm', () => {
  const wrapper = (extraProps={}) => shallow(
    <ParamsForm
      isReadOnly={false}
      isZenMode={false}
      api={{ createOauthAccessToken: jest.fn(), valueCounts: jest.fn(), _fetch: jest.fn() }}
      fields={[]}
      files={[]}
      value={{ }}
      edits={{ }}
      wfModuleId={1}
      wfModuleOutputError=''
      isWfModuleBusy={false}
      inputWfModuleId={null}
      inputDeltaId={null}
      inputColumns={[]}
      tabs={[]}
      currentTab='tab-1'
      applyQuickFix={jest.fn()}
      startCreateSecret={jest.fn()}
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
          field('c', 'string'),
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
          field('b', 'string'),
        ],
        value: {
          a: 'A',
          b: 'B',
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
          field('a', 'string'),
        ],
        value: {
          a: 'A',
        },
        edits: {
          a: 'x',
        }
      })
      w.find('Param[name="a"]').prop('onChange')('a', 'x')

      expect(w.instance().props.onChange).not.toHaveBeenCalled()
    })
  })

  describe('conditional parameter visibility', () => {
    // These tests depend on there being a WfParameter id named menu_select that is set to "Banana"
    it('should show conditional parameter matching menu value', () => {
      const w = wrapper({
        fields: [
          field('menu_select', 'menu', { enumOptions: [
            { value: 'mango', label: 'Mango' },
            'separator',
            { value: 'banana', label: 'Banana' }
          ]}),
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
          field('menu_select', 'menu', { enumOptions: [
            { value: 'mango', label: 'Mango' },
            'separator',
            { value: 'banana', label: 'Banana' }
          ]}),
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
          field('menu_select', 'menu', { enumOptions: [
            { value: 'mango', label: 'Mango' },
            'separator',
            { value: 'banana', label: 'Banana' }
          ]}),
          field('testme', 'string', { visibleIf: { idName: 'menu_select', value: [ 'banana', 'orange' ], invert: true } })
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

    it('should hide conditional parameter depending on self', () => {
      // We do this in droprowsbyposition. TODO do a migrate_params() there
      // and nix this test.
      const w = wrapper({
        fields: [
          field('testme', 'string', { visibleIf: { idName: 'testme', value: true } })
        ],
        value: {
          testme: ''
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(0)
    })

    it('should show conditional parameter depending on self', () => {
      // We do this in droprowsbyposition. TODO do a migrate_params() there
      // and nix this test.
      const w = wrapper({
        fields: [
          field('testme', 'string', { visibleIf: { idName: 'testme', value: true } })
        ],
        value: {
          testme: '1,3-9'
        }
      })
      expect(w.find('Param[name="testme"]')).toHaveLength(1)
    })
  })
})
