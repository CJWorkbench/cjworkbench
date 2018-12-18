/* globals describe, it, expect, jest, beforeEach, afterEach */
import React from 'react'
import ConnectedWfModule, { WfModule } from './WfModule'
import DataVersionModal from '../DataVersionModal'
import { okResponseMock } from '../test-utils'
import { shallow, mount } from 'enzyme'
import deepEqual from 'fast-deep-equal'
import { createStore } from 'redux'
import { Provider } from 'react-redux'
import { mockStore } from '../test-utils'
import lessonSelector from '../lessons/lessonSelector'


jest.mock('../lessons/lessonSelector', () => jest.fn()) // same mock in every test :( ... we'll live

describe('WfModule, not read-only mode', () => {
  let props
  let mockApi

  beforeEach(() => {
    mockApi = {
      addModule: jest.fn(),
      setSelectedWfModule: jest.fn(),
      postParamEvent: okResponseMock(),
    }
  })

  const buildShallowProps = () => ({
    isReadOnly: false,
    isAnonymous: false,
    isZenMode: false,
    isZenModeAllowed: false,
    moduleName: 'Load from URL',
    moduleIcon: 'icon',
    moduleHelpUrl: 'http://help-url',
    name: 'TestModule',
    wfModule: wfModule,
    module: module,
    removeModule: jest.fn(),
    inputWfModule: { id: 123, last_relevant_delta_id: 707 },
    isSelected: true,
    isAfterSelected: false,
    api: mockApi,
    index: 2,
    tabId: 11,
    onDragStart: jest.fn(),
    onDragEnd: jest.fn(),
    isLessonHighlight: false,
    isLessonHighlightCollapse: false,
    isLessonHighlightNotes: false,
    fetchModuleExists: false,
    clearNotifications: jest.fn(),
    setSelectedWfModule: jest.fn(),
    setWfModuleCollapsed: jest.fn(),
    setWfModuleParams: jest.fn(),
    setWfModuleNotes: jest.fn(),
    maybeRequestFetch: jest.fn(),
    setZenMode: jest.fn(),
    applyQuickFix: jest.fn()
  })

  // A mock module that looks like LoadURL
  const wfModule = {
    'id': 999,
    'notes': '',
    'is_collapsed': false, // false because we render more, so better test
    'is_busy': false,
    'output_status': 'ok',
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
      },
      {
        'id': 102,
        'parameter_spec': {
          'id_name': 'menu_select',
          'type': 'menu'
        },
        'value': 1,
        'items': 'Mango|Banana'
      },
      {
        'id': 103,
        'parameter_spec': {
          'id_name': 'some_boolean',
          'type': 'checkbox'
        },
        'value': true
      },
      {
        // used to test nested visibility. Test data set so param 102 makes this invisible'
        'id': 104,
        'parameter_spec': {
          'id_name': 'invisible_by_default',
          'type': 'menu',
          'visible_if': '{"id_name":"menu_select", "value": "Mango"}'
        },
        'items': 'Strawberry|Durian',
        'value': 1
      }
    ],
    module_version: { module: 2 }
  }

  beforeEach(() => {
    props = buildShallowProps()
  })

  it('matches snapshot', () => {
    const wrapper = shallow(<WfModule {...props} />)
    expect(wrapper).toMatchSnapshot()
  })

  it('is has .status-busy', () => {
    const w = shallow(<WfModule {...props} wfModule={{...wfModule, output_status: 'busy'}} />)
    expect(w.hasClass('status-busy')).toBe(true)
    expect(w.find('WfParameter').at(0).prop('wfModuleStatus')).toEqual('busy')
    expect(w.find('StatusLine').prop('status')).toEqual('busy')

    w.setProps({ wfModule: { ...wfModule, output_status: 'ok' } })
    w.update()
    expect(w.hasClass('status-busy')).toBe(false)
    expect(w.hasClass('status-ok')).toBe(true)

    expect(w.find('WfParameter').at(0).prop('wfModuleStatus')).toEqual('ok')
    expect(w.find('StatusLine').prop('status')).toEqual('ok')
    expect(w.hasClass('status-ok')).toBe(true)
    expect(w.hasClass('status-busy')).toBe(false)
  })

  it('has .status-busy overridden when wfModule.is_busy', () => {
    const w = shallow(<WfModule {...props} wfModule={{...wfModule, is_busy: true, output_status: 'ok'}} />)
    expect(w.hasClass('status-busy')).toBe(true)
  })

  it('supplies getParamText', () => {
    const wrapper = shallow(<WfModule {...props} />)
    const instance = wrapper.instance()

    expect(instance.getParamText('url')).toEqual('http://some.URL.me')
  })

  it('supplies getParamMenuItems', () => {
    const wrapper = shallow(<WfModule {...props} />)
    const instance = wrapper.instance()
    expect(instance.getParamMenuItems('menu_select')).toEqual(['Mango', 'Banana'])
  })

  it('renders a note', () => {
    const wrapper = shallow(<WfModule {...props} wfModule={Object.assign({}, wfModule, { notes: 'some notes' })} />)
    expect(wrapper.find('EditableNotes').prop('value')).toEqual('some notes')
  })

  it('renders in Zen mode', () => {
    const wrapper = shallow(<WfModule {...props} isZenMode />)
    expect(wrapper.prop('className')).toMatch(/\bzen-mode\b/)
    expect(wrapper.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ true, true, true, true ])
  })

  it('has an "enter zen mode" button', () => {
    const wrapper = shallow(<WfModule {...props} isZenModeAllowed />)
    let checkbox = wrapper.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(false)
    expect(wrapper.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ false, false, false, false ])

    checkbox.simulate('change', { target: { checked: true } })
    expect(props.setZenMode).toHaveBeenCalledWith(wfModule.id, true)
    wrapper.setProps({ isZenMode: true })

    checkbox = wrapper.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(true)
    expect(wrapper.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ true, true, true, true ])

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

    expect(props.setWfModuleNotes).toHaveBeenCalledWith(wfModule.id, 'new note')
  })

  it('deletes a note', () => {
    const wrapper = shallow(<WfModule {...props} wfModule={Object.assign({}, wfModule, { notes: 'some notes' })} />)

    expect(wrapper.find('.module-notes.visible')).toHaveLength(1)

    wrapper.find('EditableNotes').simulate('change', { target: { value: '' } })
    wrapper.find('EditableNotes').simulate('blur')

    expect(props.setWfModuleNotes).toHaveBeenCalledWith(wfModule.id, '')
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
    expect(props.setWfModuleParams).not.toHaveBeenCalled()

    wrapper.find('WfParameter[name="b"]').prop('onSubmit')()
    expect(props.setWfModuleParams).toHaveBeenCalledWith(999, { a: 'C', b: 'D' })

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

  it('submits a fetch event in WfParameter onSubmit', () => {
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

    expect(props.setWfModuleParams).toHaveBeenCalledWith(999, { url: 'http://example.org' })
    expect(props.maybeRequestFetch).toHaveBeenCalledWith(999)
  })

  it('submits a fetch in WfParameter[name=version_select] onSubmit', () => {
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

    expect(props.maybeRequestFetch).toHaveBeenCalledWith(999)
  })

  it('overrides status to busy when a fetch is pending', () => {
    const wfModule = {
      id: 999,
      notes: '',
      is_collapsed: false,
      status: 'ok',
      parameter_vals: [
        { id: 1, parameter_spec: { id_name: 'url', type: 'string' }, value: 'http://example.org' }
      ],
      nClientRequests: 1
    }
    const wrapper = shallow(<WfModule {...props} wfModule={wfModule} />)
    expect(wrapper.find('WfParameter').prop('wfModuleStatus')).toEqual('busy')
    expect(wrapper.find('StatusLine').prop('status')).toEqual('busy')
    expect(wrapper.prop('className')).toMatch(/\bstatus-busy\b/)
  })

  it('applies a quick fix', () => {
    // Scenario: user is on linechart and chose non-numeric Y axis
    const store = mockStore({
      workflow: {
        id: 99,
        tab_ids: [ 11, 12 ],
        read_only: false,
        is_anonymous: false,
        selected_tab_position: 0
      },
      tabs: {
        11: { id: 11, wf_module_ids: [ 10, 20 ] },
        12: { id: 12, wf_module_ids: [] }
      },
      wfModules: {
        10: { id: 10, tab_id: 11 },
        20: { id: 20, tab_id: 11 }
      },
      modules: {
        100: { id: 100, id_name: 'pastecsv' },
        200: { id: 200, id_name: 'linechart' },
        300: { id: 300, id_name: 'fixtype' }
      }
    }, mockApi)

    lessonSelector.mockReset()
    lessonSelector.mockReturnValue({
      testHighlight: _ => false
    })

    const w = mount(
      <Provider store={store}>
        <ConnectedWfModule
          isReadOnly={false}
          isAnonymous={false}
          isZenMode={false}
          isZenModeAllowed={false}
          index={1}
          tabId={11}
          wfModule={{ id: 20, tab_id: 11, is_collapsed: false, status: 'error', error: 'foo', quick_fixes: [{text: 'Fix', action: 'prependModule', args: ['fixtype', {foo: 'bar'}]}] }}
          isSelected={true}
          isAfterSelected={false}
          onDragStart={jest.fn()}
          onDragEnd={jest.fn()}
          setZenMode={jest.fn()}
          api={mockApi}
        />
      </Provider>
    )

    mockApi.setSelectedWfModule.mockImplementation(_ => Promise.resolve(null))
    mockApi.addModule.mockImplementation(_ => Promise.resolve(null))

    w.find('button.quick-fix').simulate('click')
    expect(mockApi.addModule).toHaveBeenCalledWith(11, 300, 1, {foo: 'bar'})
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
        workflow: {
          read_only: false,
          is_anonymous: false,
          tab_ids: [11],
          selected_tab_position: 0
        },
        tabs: {
          11: { wf_module_ids: [1, 2, 999] }
        },
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

  // Conditional UI tests
  describe('conditional parameter visibility', () => {


    // merge a visible_if block into the second parameter array of our test module
    const insertVisibleIf = (visibleIfTest) => {
      return {
        ...wfModule,
        parameter_vals: [
          wfModule.parameter_vals[0],
          {
            ...wfModule.parameter_vals[1],
            parameter_spec: {
              ...wfModule.parameter_vals[1].parameter_spec,
              visible_if: visibleIfTest
            }
          },
          wfModule.parameter_vals[2],
          wfModule.parameter_vals[3],
          wfModule.parameter_vals[4]
        ]
      }
    }

    // These depend on the test data
    const numModulesIfVisible = 4     // five params, one invisible by default
    const numModulesIfNotVisible = 3

    // These tests depend on there being a WfParameter id named menu_select that is set to "Banana"
    it('Conditional parameter visible via menu', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Banana"}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })

    it('Conditional parameter not visible via menu', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Mango"}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfNotVisible)
    })

    it('Conditional parameter not visible via inverted menu', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Banana", "invert":true}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfNotVisible)
    })

    it('Conditional parameter visible via inverted menu', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Mango", "invert":true}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })

    it('Conditional parameter visible via checkbox', () => {
      const visibleIf = '{"id_name":"some_boolean", "value":true}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })

    it('Conditional parameter invisible via inverted checkbox', () => {
      const visibleIf = '{"id_name":"some_boolean", "value":true, "invert":true}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfNotVisible)
    })

    it('Conditional parameter invisible via invisible parent', () => {
      // Even though the parent ("invisible_by_default" parameter) is set to the corrent menu item, it's not visible
      // So we shouldn't be either
      const visibleIf = '{"id_name":"invisible_by_default", "value":"Durian"}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfNotVisible)
    })

    it('Conditional parameter with bad parent name is visible', () => {
      const visibleIf = '{"id_name":"fooop", "value":"bar"}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })

    it('No infinite looop on parent name', () => {
      const visibleIf = '{"id_name":"' + wfModule.parameter_vals[1].parameter_spec.id_name + '", "value":"bar"}'
      const w = shallow( <WfModule {...props} wfModule={insertVisibleIf(visibleIf)} />)
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })

  })

})
