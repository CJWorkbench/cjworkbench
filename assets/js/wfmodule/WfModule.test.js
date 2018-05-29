jest.mock('../lessons/lessonSelector', () => jest.fn()) // same mock in every test :( ... we'll live

import React from 'react'
import ConnectedWfModule, { WfModule } from './WfModule'
import { okResponseMock } from '../test-utils'
import { shallow, mount } from 'enzyme'
import deepEqual from 'fast-deep-equal'
import { createStore } from 'redux'
import { Provider } from 'react-redux'
import lessonSelector from '../lessons/lessonSelector'

describe('WfModule, not read-only mode', () => {
  let props;
  let mockApi;

  const buildShallowProps = () => ({
    isReadOnly: false,
    name: 'TestModule',
    wfModule: wf_module,
    changeParam: mockApi.onParamChanged,
    removeModule: jest.fn(),
    revision: 707,
    selected: true,
    api: mockApi,
    connectDragSource: jest.fn(),
    connectDropTarget: jest.fn(),
    connectDragPreview: jest.fn(),
    focusModule: jest.fn(),
    startDrag: jest.fn(),
    stopDrag: jest.fn(),
    isLessonHighlight: false,
    isLessonHighlightCollapse: false,
    isLessonHighlightNotes: false,
  });

  // A mock module that looks like LoadURL
  const wf_module = {
    'id' : 999,
    'notes': [],
    'is_collapsed': false,  // false because we render more, so better test
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
        'id_name' : 'loadurl',
        'name': 'Load from URL',
      },
    }
  };


  beforeEach(() => {
    // Reset mock functions before each test
    mockApi = {
      'postParamEvent' : okResponseMock(),
      'onParamChanged' : okResponseMock()
    };

    props = buildShallowProps()
  })

  it('matches snapshot', () => {
    const wrapper = shallow(<WfModule {...props}/>)
    expect(wrapper).toMatchSnapshot();
  })

  it('is draggable', () => {
    shallow(<WfModule {...props}/>)
    expect(props.connectDragSource).toHaveBeenCalled()
    expect(props.connectDropTarget).toHaveBeenCalled()
  })

  it('auto-focuses if selected', () => {
    shallow(<WfModule {...props} selected={true}/>)
    expect(props.focusModule).toHaveBeenCalled()
  })

  it('does not auto-focus if not selected', () => {
    shallow(<WfModule {...props} selected={false}/>)
    expect(props.focusModule).not.toHaveBeenCalled()
  })

  it('supplies getParamText and setParamText', () => {
    const wrapper = shallow(<WfModule {...props}/>)
    const instance = wrapper.instance()

    expect(instance.getParamText('url')).toEqual('http://some.URL.me')
    wrapper.instance().setParamText('url', 'http://foocastle.ai');

    expect(props.changeParam).toHaveBeenCalledWith(100, { value: 'http://foocastle.ai' })
    // and the input prop should not be mutated
    expect(wf_module.parameter_vals[0].value).toEqual('http://some.URL.me')
  })

  describe('lesson highlights', () => {
    let store
    let wrapper = null
    let nonce = 0

    function highlight(selectors) {
      lessonSelector.mockReturnValue({
        testHighlight: test => {
          return selectors.some(s => deepEqual(test, s))
        }
      })

      // trigger a change
      store.dispatch({ type: 'whatever', payload: ++nonce })
      if (wrapper !== null) wrapper.update()
    }

    beforeEach(() => {
      lessonSelector.mockReset()

      // Store just needs to change, to trigger mapStateToProps. We don't care
      // about its value
      store = createStore((_, action) => action.payload)

      highlight([])

      wrapper = mount(
        <Provider store={store}>
          <ConnectedWfModule {...props} />
        </Provider>
      )
    })
    afterEach(() => {
      wrapper.unmount()
      wrapper = null
    })

    it('highlights a WfModule', () => {
      highlight([{ type: 'WfModule', moduleName: 'Load from URL' }])
      expect(wrapper.find('.wf-module').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights a WfModule', () => {
      // wrong name
      highlight([{ type: 'WfModule', moduleName: 'TestModule2' }])
      expect(wrapper.find('.wf-module').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the "collapse" button', () => {
      highlight([{ type: 'WfModuleContextButton', moduleName: 'Load from URL', button: 'collapse' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the "collapse" button', () => {
      // wrong moduleName
      highlight([{ type: 'WfModuleContextButton', moduleName: 'TestModule2', button: 'collapse' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).not.toMatch(/\blesson-highlight\b/)

      // wrong button
      highlight([{ type: 'WfModuleContextButton', moduleName: 'Load from URL', button: 'notes' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the notes button', () => {
      highlight([{ type: 'WfModuleContextButton', moduleName: 'Load from URL', button: 'notes' } ])
      expect(wrapper.find('button.edit-note').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the notes button', () => {
      // wrong moduleName
      highlight([{ type: 'WfModuleContextButton', moduleName: 'TestModule2', button: 'notes' } ])
      expect(wrapper.find('button.edit-note').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })
  })
})
