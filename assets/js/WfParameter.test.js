/* global describe, it, expect, jest */
import React from 'react'
import WfParameter from './WfParameter'
import { shallow } from 'enzyme'

describe('WfParameter', () => {


  function shallowParameter (p, paramtextReturnValue, value) {
    return shallow(
      <WfParameter
        p={p}
        isReadOnly={false}
        isZenMode={false}
        moduleName='test'
        wfModuleStatus={'ok'}
        wfModuleError={''}
        wfModuleId={1}
        inputWfModuleId={null}
        inputLastRelevantDeltaId={null}
        loggedInUser={{}}
        api={{}}
        setWfModuleParams={jest.fn()}
        getParamId={jest.fn(_ => null)}
        getParamText={jest.fn(_ => paramtextReturnValue)}
        getParamMenuItems={jest.fn(_ => ['Sugar', 'Butter', '', 'Flour'])}
        startDrag={jest.fn()}
        stopDrag={jest.fn()}
        onChange={jest.fn()}
        onSubmit={jest.fn()}
        onReset={jest.fn()}
        value={p.value || value}
      />
    )
  }

  it('Renders cell editor', () => {
    const wrapper = shallowParameter({
      visible: true,
      id: 123,
      value: '',
      parameter_spec: { type: 'custom', id_name: 'celledits' }
    })
    expect(wrapper.find('CellEditor')).toHaveLength(1)
    expect(wrapper).toMatchSnapshot()
  })

  it('Renders string input field', () => {
    const wrapper = shallowParameter({
      visible: true,
      id: 123,
      value: 'data.sfgov.org',
      parameter_spec: {type: 'string', id_name: 'url'}
    })
    expect(wrapper.find('SingleLineTextField')).toHaveLength(1)
    expect(wrapper).toMatchSnapshot()
  })

  it('Should render a "colnames" parameter that has type string', () => {
    var wrapper = shallowParameter({
      visible: true,
      id: 123,
      value: 'A,B,C',
      parameter_spec: {
        id_name: 'colnames',
        type: 'string'
      }
    }, 'A,B,C');
    expect(wrapper.find('ColumnSelector')).toHaveLength(1);
  })

  it('Should not render a "colselect" parameter that has type multicolumn', () => {
    var wrapper = shallowParameter({
      visible: true,
      id: 123,
      value: '',
      parameter_spec: {
        id_name: 'colselect',
        type: 'multicolumn',
      }
    }, '')
    expect(wrapper.find('ColumnSelector')).toHaveLength(0);
  })
})
