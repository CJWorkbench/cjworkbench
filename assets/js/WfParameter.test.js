/* global describe, it, expect, jest */
import React from 'react'
import WfParameter from './WfParameter'
import { shallow } from 'enzyme'

describe('WfParameter', () => {
  // For testing conditional UI
  const visibilityCond1 = {
    'id_name': 'whatever',
    'value': 'Butter|Flour'
  }
  const visibilityCond2 = {
    'id_name': 'whatever',
    'value': 'Sugar'
  }
  const visibilityCond3 = {
    'id_name': 'whatever',
    'value': true
  }
  const visibilityCond4 = {
    'id_name': 'whatever',
    'value': false
  }

  function shallowParameter (p, paramtextReturnValue, value) {
    return shallow(
      <WfParameter
        p={p}
        isReadOnly={false}
        isZenMode={false}
        moduleName='test'
        wfModuleStatus={'ready'}
        wfModuleError={''}
        wfModuleId={1}
        inputWfModuleId={null}
        inputLastRelevantDeltaId={null}
        loggedInUser={{}}
        api={{}}
        changeParam={jest.fn()}
        getParamId={jest.fn(_ => null)}
        getParamText={jest.fn(_ => paramtextReturnValue)}
        setParamText={jest.fn()}
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

  // Conditional UI tests

  it('Renders a parameter when visible_if conditions are met', () => {
    const wrapper = shallowParameter({
      visible: true,
      id: 123,
      value: 'data.sfgov.org',
      parameter_spec: {
        id_name: 'url',
        type: 'string',
        visible_if: JSON.stringify(visibilityCond1)
      }
    }, 3)
    expect(wrapper.find('SingleLineTextField')).toHaveLength(1)
  })

  it('Does not render a parameter when visible_if conditions are not met', () => {
    var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond2),
        }
    }, 3);
    expect(wrapper.find('SingleLineTextField')).toHaveLength(0);
  });

  it('Does not render a parameter when visible_if conditions are met but visible_if is inverted', () => {
      var newVisibilityCond = Object.assign(visibilityCond1, {});
      newVisibilityCond['invert'] = true;
      var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(newVisibilityCond),
        }
    }, 3);
    expect(wrapper.find('SingleLineTextField')).toHaveLength(0);
  });

  it('Renders a parameter when visible_if conditions are not met but visible_if is inverted', () => {
      var newVisibilityCond = Object.assign(visibilityCond2, {});
      newVisibilityCond['invert'] = true;
      var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(newVisibilityCond),
        }
    }, 3);
    expect(wrapper.find('SingleLineTextField')).toHaveLength(1);
  });

  it('Renders a parameter when boolean visible_if conditions are met', () => {
      var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond3),
        }
    }, 'a value');
    expect(wrapper.find('SingleLineTextField')).toHaveLength(1);
  });

  it('It does not render a parameter when boolean visible_if conditions are not met', () => {
      var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond3),
        }
    }, '');
    expect(wrapper.find('SingleLineTextField')).toHaveLength(0);
  });
  it('Renders a parameter when boolean visible_if conditions are met for non-bool dependency (true)', () => {
      var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond3),
        }
    }, 'There is text');
    expect(wrapper.find('SingleLineTextField')).toHaveLength(1);
  });
  it('Does not render a parameter when boolean visible_if conditions are not met for non-bool dependency (true)', () => {
      var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond3),
        }
    }, '');
    expect(wrapper.find('SingleLineTextField')).toHaveLength(0);
  });
  it('Renders a parameter when boolean visible_if condition met for non-bool dependency (false)', () => {
      var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond4),
        }
    }, '');
    expect(wrapper.find('SingleLineTextField')).toHaveLength(1);
  });
  it('Does not render a parameter when boolean visible_if conditions are not met for non-bool dependency (false)', () => {
      var wrapper = shallowParameter({
        visible: true,
        id: 123,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond4),
        }
    }, 'There is text');
    expect(wrapper.find('SingleLineTextField')).toHaveLength(0);
  });
});

