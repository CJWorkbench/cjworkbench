import React from 'react'
import { WfModule } from './WfModule'
import { okResponseMock } from '../utils'
import { mount } from 'enzyme'

describe('WfModule, not read-only mode', () => {

  let wrapper;
  let props;
  let mockApi;

  // A mock module that looks like LoadURL
  var wf_module = {
    'id' : 999,
    'notes': [],
    'parameter_vals': [
      {
        'id': 100,
        'parameter_spec': {
          'id_name': 'url',
          'type': 'string'
        }
      },
      {
        'id': 101,
        'parameter_spec': {
          'id_name': 'version_select',
          'type': 'custom'
        }
      }
    ],
    'module_version' : {
      'module' : {
        'id_name' : 'loadurl'
      },
    }
  };


  beforeEach(() => {
    // Reset mock functions before each test
    mockApi = {
      'postParamEvent' : okResponseMock(),
      'onParamChanged' : okResponseMock()
    };

    props = {
        'data-isReadOnly': false,
        'data-wfmodule': wf_module,
        'data-changeParam': mockApi.onParamChanged,
        'data-removeModule':  () => {} ,
        'data-revision': 707,
        'data-selected': true,
        'data-api': mockApi,
        'connectDragSource': jest.fn(),
        'connectDropTarget': jest.fn(),
        'connectDragPreview': jest.fn(),
        'focusModule': jest.fn(),
        'startDrag' : jest.fn(),
        'stopDrag' : jest.fn()
      };

    wrapper = mount(
      <WfModule
        {...props}
      />
    )
  });

  it('Renders and calls functions on componentDidMount and render', () => {
    expect(wrapper).toMatchSnapshot();
    expect(props.connectDragSource.mock.calls.length).toBe(1);
    expect(props.connectDropTarget.mock.calls.length).toBe(1);
    expect(props.focusModule.mock.calls.length).toBe(1);
  });

});
