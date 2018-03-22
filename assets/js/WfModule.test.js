import React from 'react'
import { WfModule } from './wfmodule/WfModule'
import { mount } from 'enzyme'

describe('WfModule, NOT read-only mode - DUMMY TEST ONLY', () => {

  var wrapper;
  var props = {
        'data-isReadOnly': false,
        'data-wfmodule': {
          'notes': [],
          'parameter_vals': [],
          'module_version': {
            'module': {},
          }
        },
        'data-changeParam': () => {} ,
        'data-removeModule':  () => {} ,
        'data-revision': 707,
        'data-selected': true,
        'data-api': {},
        'connectDragSource': jest.fn(),
        'connectDropTarget': jest.fn(),
        'focusModule': jest.fn(),
      };

  beforeEach(() => {
    wrapper = mount(
      <WfModule
        {...props}
      />
    )
  });

  it('Renders and calls functions on componentDidMount and render', () => {
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.props().connectDragSource.mock.calls.length).toBe(1);
    expect(wrapper.props().connectDropTarget.mock.calls.length).toBe(1);
    expect(wrapper.props().focusModule.mock.calls.length).toBe(1);
  });

});
