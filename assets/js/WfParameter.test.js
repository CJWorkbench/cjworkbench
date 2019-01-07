/* global describe, it, expect, jest */
import React from 'react'
import WfParameter from './WfParameter'
import { shallow } from 'enzyme'

describe('WfParameter', () => {
  function shallowParameter (extraProps) {
    return shallow(
      <WfParameter
        name='name'
        idName='idName'
        placeholder='placeholder'
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
        deleteSecret={jest.fn()}
        applyQuickFix={jest.fn()}
        startCreateSecret={jest.fn()}
        setWfModuleParams={jest.fn()}
        getParamText={jest.fn()}
        deleteSecret={jest.fn()}
        startCreateSecret={jest.fn()}
        startDrag={jest.fn()}
        stopDrag={jest.fn()}
        onChange={jest.fn()}
        onSubmit={jest.fn()}
        onReset={jest.fn()}
        value={null}
        {...extraProps}
      />
    )
  }

  it('should render a cell editor', () => {
    const wrapper = shallowParameter({
      idName: 'celledits',
      type: 'custom',
      value: ''
    })
    expect(wrapper.find('CellEditor')).toHaveLength(1)
  })

  it('should render a string input field', () => {
    const wrapper = shallowParameter({
      type: 'string',
      value: 'data.sfgov.org',
    })
    expect(wrapper.find('SingleLineTextField')).toHaveLength(1)
  })
})
