import React from 'react'
import { WfModule } from './WfModule'
import { okResponseMock } from './utils'
import { mount } from 'enzyme'

describe('WfModule, not read-only mode', () => {

  let wrapper;
  let props;
  let mockApi;

  // A basic mock module, set up to test the slightly gnarly press enter on URL field = press URL fetch button logic
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
        'focusModule': jest.fn(),
        'toggleDrag' : jest.fn()
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

  // Hardcoded logic where the url parameter communicates with the version select parameter
  it('pressing enter on a URL field fetches', (done) => {

    expect(wf_module.module_version.module.id_name).toBe('loadurl');
    let id = wf_module.parameter_vals[0].id;
    let paramIdName = wf_module.parameter_vals[0].parameter_spec.id_name;
    expect(paramIdName).toBe('url');
    let payload = { 'value' : 'foo' };

    let pressedEnter = false;
    wrapper.instance().changeParam(id, paramIdName, payload, pressedEnter);
    expect(mockApi.postParamEvent.mock.calls.length).toBe(0); // didn't press enter, no click event

    pressedEnter = true;
    wrapper.instance().changeParam(id, paramIdName, payload, pressedEnter);

    // setImmediate b/c changeParam waits for onParamChanged to complete before postParamEvent -- hence a promise
    setImmediate( () => {
      expect(mockApi.postParamEvent.mock.calls.length).toBe(1); // enter on url field, fetch data
      done();
    });
  });

});
