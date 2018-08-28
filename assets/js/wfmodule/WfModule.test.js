/* globals describe, it, expect, jest, beforeEach, afterEach */
import React from 'react'
import ConnectedWfModule, { WfModule } from './WfModule'
import DataVersionModal from '../DataVersionModal'
import { okResponseMock } from '../test-utils'
import { shallow, mount } from 'enzyme'
import deepEqual from 'fast-deep-equal'
import { createStore } from 'redux'
import { Provider } from 'react-redux'
import lessonSelector from '../lessons/lessonSelector'

jest.mock('../lessons/lessonSelector', () => jest.fn()) // same mock in every test :( ... we'll live

describe('WfModule, not read-only mode', () => {
  let props
  let mockApi

  const buildShallowProps = () => ({
    isReadOnly: false,
    isAnonymous: false,
    isZenMode: false,
    name: 'TestModule',
    wfModule: wfModule,
    module: module,
    changeParam: jest.fn(),
    removeModule: jest.fn(),
    inputWfModule: { id: 123, last_relevant_delta_id: 707 },
    selected: true,
    api: mockApi,
    index: 2,
    onDragStart: jest.fn(),
    onDragEnd: jest.fn(),
    isLessonHighlight: false,
    isLessonHighlightCollapse: false,
    isLessonHighlightNotes: false,
    fetchModuleExists: false,
    clearNotifications: jest.fn(),
    setSelectedWfModule: jest.fn(),
    setWfModuleCollapsed: jest.fn(),
    setZenMode: jest.fn()
  })

  // A mock module that looks like LoadURL
  const wfModule = {
    'id': 999,
    'notes': '',
    'is_collapsed': false, // false because we render more, so better test
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
    module_version: { module: 2 }
  }

  const module = { id_name: 'loadurl', name: 'Load from URL' }

  beforeEach(() => {
    // Reset mock functions before each test
    mockApi = {
      postParamEvent: okResponseMock(),
      onParamChanged: okResponseMock(),
      setWfModuleNotes: okResponseMock()
    }

    props = buildShallowProps()
  })

  it('matches snapshot', () => {
    const wrapper = shallow(<WfModule {...props} />)
    expect(wrapper).toMatchSnapshot()
  })

  it('is has .status-busy', () => {
    const w = shallow(<WfModule {...props} wfModule={{...wfModule, status: 'busy'}} />)
    expect(w.hasClass('status-busy')).toBe(true)
    w.setProps({ wfModule: { ...wfModule, status: 'ready' } })
    w.update()
    expect(w.hasClass('status-busy')).toBe(false)
    expect(w.hasClass('status-ready')).toBe(true)
  })

  it('supplies getParamText and setParamText', () => {
    const wrapper = shallow(<WfModule {...props} />)
    const instance = wrapper.instance()

    expect(instance.getParamText('url')).toEqual('http://some.URL.me')
    wrapper.instance().setParamText('url', 'http://foocastle.ai')

    expect(props.changeParam).toHaveBeenCalledWith(100, { value: 'http://foocastle.ai' })
    // and the input prop should not be mutated
    expect(wfModule.parameter_vals[0].value).toEqual('http://some.URL.me')
  })

  it('renders a note', () => {
    const wrapper = shallow(<WfModule {...props} wfModule={Object.assign({}, wfModule, { notes: 'some notes' })} />)
    expect(wrapper.find('EditableNotes').prop('value')).toEqual('some notes')
  })

  it('renders in Zen mode', () => {
    const wrapper = shallow(<WfModule {...props} isZenMode />)
    expect(wrapper.prop('className')).toMatch(/\bzen-mode\b/)
    expect(wrapper.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ true, true ])
  })

  it('has an "enter zen mode" button', () => {
    const aModule = { id_name: 'pythoncode', name: 'Python Code', has_zen_mode: true }
    const wrapper = shallow(<WfModule {...props} module={aModule} />)
    let checkbox = wrapper.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(false)
    expect(wrapper.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ false, false ])

    checkbox.simulate('change', { target: { checked: true } })
    expect(props.setZenMode).toHaveBeenCalledWith(wfModule.id, true)
    wrapper.setProps({ isZenMode: true })

    checkbox = wrapper.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(true)
    expect(wrapper.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ true, true ])

    checkbox.simulate('change', { target: { checked: false } })
    expect(props.setZenMode).toHaveBeenCalledWith(wfModule.id, false)
  })

  it('renders notifications, opening and closing a modal', () => {
    const wrapper = shallow(<WfModule {...props} fetchModuleExists isReadOnly={false} isAnonymous={false} />)

    wrapper.find('button.notifications').simulate('click')
    expect(props.clearNotifications).toHaveBeenCalledWith(999)
    expect(wrapper.find(DataVersionModal).length).toBe(1)

    wrapper.find(DataVersionModal).prop('onClose')()
    wrapper.update()
    expect(wrapper.find(DataVersionModal).length).toBe(0)
  })

  it('hides notifications when isAnonymous', () => {
    const wrapper = shallow(<WfModule {...props} fetchModuleExists isReadOnly={false} isAnonymous />)
    expect(wrapper.find('button.notifications').length).toBe(0)
  })

  it('hides notifications when isReadOnly', () => {
    const wrapper = shallow(<WfModule {...props} fetchModuleExists isReadOnly isAnonymous={false} />)
    expect(wrapper.find('button.notifications').length).toBe(0)
  })

  it('hides notifications when there is no fetch module', () => {
    const wrapper = shallow(<WfModule {...props} fetchModuleExists={false} isReadOnly={false} isAnonymous={false} />)
    expect(wrapper.find('button.notifications').length).toBe(0)
  })

  it('adds a note', () => {
    const wrapper = shallow(<WfModule {...props} />)

    expect(wrapper.find('.module-notes.visible')).toHaveLength(0)

    wrapper.find('button.edit-note').simulate('click')
    wrapper.find('EditableNotes').simulate('change', { target: { value: 'new note' } })
    wrapper.find('EditableNotes').simulate('blur')

    expect(wrapper.find('EditableNotes').prop('value')).toEqual('new note')
    expect(mockApi.setWfModuleNotes).toHaveBeenCalledWith(wfModule.id, 'new note')

    expect(wrapper.find('.module-notes.visible')).toHaveLength(1)
  })

  it('deletes a note', () => {
    const wrapper = shallow(<WfModule {...props} wfModule={Object.assign({}, wfModule, { notes: 'some notes' })} />)

    expect(wrapper.find('.module-notes.visible')).toHaveLength(1)

    wrapper.find('EditableNotes').simulate('change', { target: { value: '' } })
    wrapper.find('EditableNotes').simulate('blur')

    expect(wrapper.find('EditableNotes').prop('value')).toEqual('')
    expect(mockApi.setWfModuleNotes).toHaveBeenCalledWith(wfModule.id, '')

    expect(wrapper.find('.module-notes.visible')).toHaveLength(0)
  })

  it('queues changes from onChange and then submits them in onSubmit', () => {
    const wfModule = {
      id: 999,
      notes: '',
      is_collapsed: false,
      parameter_vals: [
        { id: 1, parameter_spec: { id_name: 'a', type: 'string' }, value: 'A' },
        { id: 2, parameter_spec: { id_name: 'b', type: 'String' }, value: 'B' }
      ]
    }
    const wrapper = shallow(
      <WfModule
        {...props}
        wfModule={wfModule}
      />
    )

    wrapper.find('WfParameter[name="a"]').prop('onChange')('a', 'C')
    wrapper.update()
    expect(wrapper.find('WfParameter[name="a"]').prop('value')).toEqual('C')

    wrapper.find('WfParameter[name="b"]').prop('onChange')('b', 'D')
    wrapper.update()
    expect(wrapper.find('WfParameter[name="b"]').prop('value')).toEqual('D')

    // ... and neither should be submitted to the server
    expect(props.changeParam).not.toHaveBeenCalled()

    wrapper.find('WfParameter[name="b"]').prop('onSubmit')()
    expect(props.changeParam).toHaveBeenCalledWith(1, 'C')
    expect(props.changeParam).toHaveBeenCalledWith(2, 'D')

    // a bit of a white-box test: state should be cleared
    expect(wrapper.state('edits')).toEqual({})
  })

  it('resets just the one WfParmeter in onReset', () => {
    const wfModule = {
      id: 999,
      notes: '',
      is_collapsed: false,
      parameter_vals: [
        { id: 1, parameter_spec: { id_name: 'a', type: 'string' }, value: 'A' },
        { id: 2, parameter_spec: { id_name: 'b', type: 'String' }, value: 'B' }
      ]
    }
    const wrapper = shallow(
      <WfModule
        {...props}
        wfModule={wfModule}
      />
    )

    wrapper.find('WfParameter[name="a"]').prop('onChange')('a', 'C')
    wrapper.find('WfParameter[name="b"]').prop('onChange')('b', 'D')
    wrapper.update()
    wrapper.find('WfParameter[name="b"]').prop('onReset')('b')
    wrapper.update()
    expect(wrapper.find('WfParameter[name="a"]').prop('value')).toEqual('C')
    expect(wrapper.find('WfParameter[name="b"]').prop('value')).toEqual('B')
  })

  it('submits a fake version_select click event in WfParameter onSubmit', () => {
    // Use case:
    // 1. User edits url field
    // 2. User clicks "submit" button within the URL field
    // Expected behavior: same as if user clicks "submit" button in the
    // WfParameter
    const wfModule = {
      id: 999,
      notes: '',
      is_collapsed: false,
      parameter_vals: [
        { id: 1, parameter_spec: { id_name: 'url', type: 'string' }, value: '' },
        { id: 2, parameter_spec: { id_name: 'version_select', type: 'String' }, value: 'B' }
      ]
    }
    const wrapper = shallow(
      <WfModule
        {...props}
        wfModule={wfModule}
      />
    )

    wrapper.find('WfParameter[name="url"]').prop('onChange')('url', 'http://example.org')
    wrapper.find('WfParameter[name="url"]').prop('onSubmit')()

    expect(props.changeParam).toHaveBeenCalledWith(1, 'http://example.org')
    expect(mockApi.postParamEvent).toHaveBeenCalledWith(2)
  })

  it('submits a version_select click event in WfParameter[name=version_select] onSubmit', () => {
    // Use case: user wants to re-fetch
    const wfModule = {
      id: 999,
      notes: '',
      is_collapsed: false,
      parameter_vals: [
        { id: 1, parameter_spec: { id_name: 'url', type: 'string' }, value: 'http://example.org' },
        { id: 2, parameter_spec: { id_name: 'version_select', type: 'String' }, value: 'B' }
      ]
    }
    const wrapper = shallow(
      <WfModule
        {...props}
        wfModule={wfModule}
      />
    )

    wrapper.find('WfParameter[name="version_select"]').prop('onSubmit')()

    expect(mockApi.postParamEvent).toHaveBeenCalledWith(2)
  })

  describe('lesson highlights', () => {
    let store
    let wrapper = null
    let nonce = 0

    function highlight (selectors) {
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

      store = createStore((_, action) => ({
        workflow: { read_only: false, is_anonymous: false, wf_modules: [1, 2, 999] },
        wfModules: {
          999: { module_version: { module: 2 } }
        },
        modules: { 2: { name: 'Load from URL' } },
        ...action.payload
      }))

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
      highlight([{ type: 'WfModule', index: 2, moduleName: 'Load from URL' }])
      expect(wrapper.find('.wf-module').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights a WfModule', () => {
      // wrong name
      highlight([{ type: 'WfModule', index: 2, moduleName: 'TestModule2' }])
      expect(wrapper.find('.wf-module').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the "collapse" button', () => {
      highlight([{ type: 'WfModuleContextButton', index: 2, moduleName: 'Load from URL', button: 'collapse' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the "collapse" button', () => {
      // wrong moduleName
      highlight([{ type: 'WfModuleContextButton', index: 2, moduleName: 'TestModule2', button: 'collapse' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).not.toMatch(/\blesson-highlight\b/)

      // wrong button
      highlight([{ type: 'WfModuleContextButton', index: 2, moduleName: 'Load from URL', button: 'notes' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the notes button', () => {
      highlight([{ type: 'WfModuleContextButton', index: 2, moduleName: 'Load from URL', button: 'notes' }])
      expect(wrapper.find('button.edit-note').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the notes button', () => {
      // wrong moduleName
      highlight([{ type: 'WfModuleContextButton', index: 2, moduleName: 'TestModule2', button: 'notes' }])
      expect(wrapper.find('button.edit-note').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })
  })
})
