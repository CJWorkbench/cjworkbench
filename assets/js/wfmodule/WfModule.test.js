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
    changeParam: mockApi.onParamChanged,
    removeModule: jest.fn(),
    revision: 707,
    selected: true,
    api: mockApi,
    index: 2,
    focusModule: jest.fn(),
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
    'module_version': {
      'module': {
        'id_name': 'loadurl',
        'name': 'Load from URL'
      }
    }
  }

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

  it('auto-focuses if selected', () => {
    shallow(<WfModule {...props} selected />)
    expect(props.focusModule).toHaveBeenCalled()
  })

  it('does not auto-focus if not selected', () => {
    shallow(<WfModule {...props} selected={false} />)
    expect(props.focusModule).not.toHaveBeenCalled()
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
    const aWfModule = Object.assign({}, wfModule, {
      module_version: {
        module: {
          id_name: 'pythoncode',
          name: 'Python Code'
        }
      }
    })

    const wrapper = shallow(<WfModule {...props} wfModule={aWfModule} />)
    let checkbox = wrapper.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(false)
    expect(wrapper.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ false, false ])

    checkbox.simulate('change', { target: { checked: true } })
    expect(props.setZenMode).toHaveBeenCalledWith(aWfModule.id, true)
    wrapper.setProps({ isZenMode: true })

    checkbox = wrapper.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(true)
    expect(wrapper.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ true, true ])

    checkbox.simulate('change', { target: { checked: false } })
    expect(props.setZenMode).toHaveBeenCalledWith(aWfModule.id, false)
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

      // Store just needs to change, to trigger mapStateToProps. We don't care
      // about its value
      store = createStore((_, action) => ({
        workflow: { read_only: false, is_anonymous: false, wf_modules: [] },
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
