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
        },
        'value': 'http://some.URL.me'
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
        isReadOnly: false,
        name: 'TestModule',
        wfModule: wf_module,
        changeParam: mockApi.onParamChanged,
        removeModule:  () => {} ,
        revision: 707,
        selected: true,
        api: mockApi,
        connectDragSource:  jest.fn(),
        connectDropTarget:  jest.fn(),
        connectDragPreview: jest.fn(),
        focusModule:        jest.fn(),
        startDrag :         jest.fn(),
        stopDrag :          jest.fn()
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

  it('getParamText and setParamText', () => {
    expect(wrapper.instance().getParamText('url')).toBe(wf_module.parameter_vals[0].value);

    wrapper.instance().setParamText('url','http://foocastle.ai');
    expect(props.changeParam.mock.calls.length).toBe(1);
    expect(props.changeParam.mock.calls[0][0]).toEqual(wf_module.parameter_vals[0].id);  // should translate id_name to id
    expect(props.changeParam.mock.calls[0][1]).toEqual({'value' : 'http://foocastle.ai'});
  })

});
