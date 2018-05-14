import React from 'react'
import { WfModule, mapStateToProps } from './WfModule'
import { okResponseMock } from '../utils'
import { shallow } from 'enzyme'

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
  })

  // A mock module that looks like LoadURL
  const wf_module = {
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

  describe('mapStateToProps', () => {
    it('should set isLessonHighlight=true', () => {
      expect(mapStateToProps(
        { lesson_highlight: [ { type: 'WfModule', moduleName: 'Load from URL' } ] },
        buildShallowProps()
      ).isLessonHighlight).toBe(true)
    })

    it('should set isLessonHighlight=false', () => {
      expect(mapStateToProps(
        { lesson_highlight: [ { type: 'WfModule', moduleName: 'Anything but "Load from URL"' } ] },
        buildShallowProps()
      ).isLessonHighlight).toBe(false)
    })

    it('should set isLessonHighlightCollapse=true', () => {
      expect(mapStateToProps(
        { lesson_highlight: [ { type: 'WfModuleContextButton', moduleName: 'Load from URL', button: 'collapse' } ] },
        buildShallowProps()
      ).isLessonHighlightCollapse).toBe(true)
    })

    it('should set isLessonHighlightCollapse=false', () => {
      expect(mapStateToProps(
        { lesson_highlight: [ { type: 'WfModuleContextButton', moduleName: 'Load from URL', button: 'notes' } ] },
        buildShallowProps()
      ).isLessonHighlightCollapse).toBe(false)
    })

    it('should set isLessonHighlightNotes=true', () => {
      expect(mapStateToProps(
        { lesson_highlight: [ { type: 'WfModuleContextButton', moduleName: 'Load from URL', button: 'notes' } ] },
        buildShallowProps()
      ).isLessonHighlightNotes).toBe(true)
    })

    it('should set isLessonHighlightNotes=false', () => {
      expect(mapStateToProps(
        { lesson_highlight: [ { type: 'WfModuleContextButton', moduleName: 'Load from URL', button: 'collapse' } ] },
        buildShallowProps()
      ).isLessonHighlightNotes).toBe(false)
    })
  })
})
