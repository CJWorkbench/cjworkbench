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
  let mockApi

  beforeEach(() => {
    mockApi = {
      addModule: jest.fn(),
      setSelectedWfModule: jest.fn(),
      postParamEvent: okResponseMock(),
    }
  })

  // A mock module that looks like LoadURL
  const wfModule = {
    id: 999,
    notes: '',
    is_collapsed: false, // false because we render more, so better test
    is_busy: false,
    output_status: 'ok',
    params: {
      url: 'http://some.URL.me',
      version_select: null,
      menu_select: 1,
      some_boolean: true,
      invisible_by_default: 1
    }
  }

  function pspec (idName, type, extraProps={}) {
    return {
      id_name: idName,
      type,
      multiline: false,
      placeholder: '',
      visible_if: '',
      ...extraProps
    }
  }

  const module = {
    id_name: 'loadurl', // more or less
    name: 'Load from URL',
    icon: 'icon',
    help_url: 'http://help-url',
    parameter_specs: [
      pspec('url', 'string'),
      pspec('version_select', 'custom'),
      pspec('menu_select', 'menu', { items: 'Mango|Banana' }),
      pspec('some_boolean', 'checkbox'),
      // used to test nested visibility. Test data set so param 'menu_select' makes this invisible'
      pspec('invisible_by_default', 'menu', {
        'items': 'Strawberry|Durian',
        'visible_if': '{"id_name": "menu_select", "value": "Mango"}'
      })
    ],
  }

  const wrapper = (extraProps={}) => {
    return shallow(
      <WfModule
        isReadOnly={false}
        isAnonymous={false}
        isZenMode={false}
        isZenModeAllowed={false}
        module={module}
        wfModule={wfModule}
        removeModule={jest.fn()}
        inputWfModule={{ id: 123, last_relevant_delta_id: 707 }}
        isSelected
        isAfterSelected={false}
        api={mockApi}
        index={2}
        tabId={11}
        onDragStart={jest.fn()}
        onDragEnd={jest.fn()}
        isLessonHighlight={false}
        isLessonHighlightCollapse={false}
        isLessonHighlightNotes={false}
        fetchModuleExists={false}
        clearNotifications={jest.fn()}
        setSelectedWfModule={jest.fn()}
        setWfModuleCollapsed={jest.fn()}
        setWfModuleParams={jest.fn()}
        setWfModuleNotes={jest.fn()}
        maybeRequestFetch={jest.fn()}
        setZenMode={jest.fn()}
        applyQuickFix={jest.fn()}
        {...extraProps}
      />
    )
  }

  it('matches snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('is has .status-busy', () => {
    const w = wrapper({ wfModule: { ...wfModule, output_status: 'busy' } })
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
    const w = wrapper({ wfModule: { ...wfModule, output_status: 'ok', is_busy: true } })
    expect(w.hasClass('status-busy')).toBe(true)
  })

  it('supplies getParamText', () => {
    const w = wrapper({ wfModule: { ...wfModule, params: { 'x': 'y' }}})
    const instance = w.instance()

    expect(instance.getParamText('x')).toEqual('y')
  })

  it('renders a note', () => {
    const w = wrapper({ wfModule: { ...wfModule, notes: 'some notes' } })
    expect(w.find('EditableNotes').prop('value')).toEqual('some notes')
  })

  it('renders in Zen mode', () => {
    const w = wrapper({ isZenMode: true })
    expect(w.prop('className')).toMatch(/\bzen-mode\b/)
    expect(w.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ true, true, true, true ])
  })

  it('has an "enter zen mode" button', () => {
    const w = wrapper({ isZenModeAllowed: true })
    let checkbox = w.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(false)
    expect(w.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ false, false, false, false ])

    checkbox.simulate('change', { target: { checked: true } })
    expect(w.instance().props.setZenMode).toHaveBeenCalledWith(wfModule.id, true)
    w.setProps({ isZenMode: true })

    checkbox = w.find('input[type="checkbox"][name="zen-mode"]')
    expect(checkbox.prop('checked')).toBe(true)
    expect(w.find('WfParameter').map(n => n.prop('isZenMode'))).toEqual([ true, true, true, true ])

    checkbox.simulate('change', { target: { checked: false } })
    expect(w.instance().props.setZenMode).toHaveBeenCalledWith(wfModule.id, false)
  })

  it('renders notifications, opening and closing a modal', () => {
    const w = wrapper({ fetchModuleExists: true, isReadOnly: false, isAnonymous: false })

    w.find('button.notifications').simulate('click')
    expect(w.instance().props.clearNotifications).toHaveBeenCalledWith(999)
    expect(w.find(DataVersionModal).length).toBe(1)

    w.find(DataVersionModal).prop('onClose')()
    w.update()
    expect(w.find(DataVersionModal).length).toBe(0)
  })

  it('hides notifications when isAnonymous', () => {
    const w = wrapper({ fetchModuleExists: true, isReadOnly: false, isAnonymous: true })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('hides notifications when isReadOnly', () => {
    const w = wrapper({ fetchModuleExists: true, isReadOnly: true, isAnonymous: false })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('hides notifications when there is no fetch module', () => {
    const w = wrapper({ fetchModuleExists: false, isReadOnly: false, isAnonymous: false })
    expect(w.find('button.notifications').length).toBe(0)
  })

  it('adds a note', () => {
    const w = wrapper({ wfModule: { ...wfModule, notes: '' }})

    expect(w.find('.module-notes.visible')).toHaveLength(0)

    w.find('button.edit-note').simulate('click')
    w.find('EditableNotes').simulate('change', { target: { value: 'new note' } })
    w.find('EditableNotes').simulate('blur')

    expect(w.instance().props.setWfModuleNotes).toHaveBeenCalledWith(wfModule.id, 'new note')
  })

  it('deletes a note', () => {
    const w = wrapper({ wfModule: { ...wfModule, notes: 'some notes' }})

    expect(w.find('.module-notes.visible')).toHaveLength(1)

    w.find('EditableNotes').simulate('change', { target: { value: '' } })
    w.find('EditableNotes').simulate('blur')

    expect(w.instance().props.setWfModuleNotes).toHaveBeenCalledWith(wfModule.id, '')
  })

  it('queues changes from onChange and then submits them in onSubmit', () => {
    const wfModule = {
      id: 999,
      notes: '',
      is_collapsed: false,
      params: {
        a: 'A',
        b: 'B'
      }
    }
    const aModule = {
      ...module,
      parameter_specs: [ pspec('a', 'string'), pspec('b', 'string') ]
    }
    const w = wrapper({ wfModule, module: aModule })

    w.find('WfParameter[idName="a"]').prop('onChange')('a', 'C')
    w.update()
    expect(w.find('WfParameter[idName="a"]').prop('value')).toEqual('C')

    w.find('WfParameter[idName="b"]').prop('onChange')('b', 'D')
    w.update()
    expect(w.find('WfParameter[idName="b"]').prop('value')).toEqual('D')

    // ... and neither should be submitted to the server
    expect(w.instance().props.setWfModuleParams).not.toHaveBeenCalled()

    w.find('WfParameter[idName="b"]').prop('onSubmit')()
    expect(w.instance().props.setWfModuleParams).toHaveBeenCalledWith(999, { a: 'C', b: 'D' })

    // a bit of a white-box test: state should be cleared
    expect(w.state('edits')).toEqual({})
  })

  it('resets just the one WfParmeter in onReset', () => {
    const wfModule = {
      id: 999,
      notes: '',
      is_collapsed: false,
      params: {
        a: 'A',
        b: 'B'
      }
    }
    const aModule = {
      ...module,
      parameter_specs: [ pspec('a', 'string'), pspec('b', 'string') ]
    }
    const w = wrapper({ wfModule, module: aModule })

    w.find('WfParameter[idName="a"]').prop('onChange')('a', 'C')
    w.find('WfParameter[idName="b"]').prop('onChange')('b', 'D')
    w.update()
    w.find('WfParameter[idName="b"]').prop('onReset')('b')
    w.update()
    expect(w.find('WfParameter[idName="a"]').prop('value')).toEqual('C')
    expect(w.find('WfParameter[idName="b"]').prop('value')).toEqual('B')
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
      params: {
        url: '',
        version_select: 'B'
      }
    }
    const aModule = {
      ...module,
      parameter_specs: [ pspec('url', 'string'), pspec('version_select', 'custom') ]
    }
    const w = wrapper({ wfModule, module: aModule })

    w.find('WfParameter[idName="url"]').prop('onChange')('url', 'http://example.org')
    w.find('WfParameter[idName="url"]').prop('onSubmit')()

    expect(w.instance().props.setWfModuleParams).toHaveBeenCalledWith(999, { url: 'http://example.org' })
    expect(w.instance().props.maybeRequestFetch).toHaveBeenCalledWith(999)
  })

  it('submits a fetch in WfParameter[idName=version_select] onSubmit', () => {
    // Use case: user wants to re-fetch
    const wfModule = {
      id: 999,
      notes: '',
      is_collapsed: false,
      params: {
        url: '',
        version_select: 'B'
      }
    }
    const aModule = {
      ...module,
      parameter_specs: [ pspec('url', 'string'), pspec('version_select', 'custom') ]
    }
    const w = wrapper({ wfModule, module: aModule })

    w.find('WfParameter[idName="version_select"]').prop('onSubmit')()

    expect(w.instance().props.maybeRequestFetch).toHaveBeenCalledWith(999)
  })

  it('overrides status to busy when a fetch is pending', () => {
    const w = wrapper({ wfModule: { ...wfModule, nClientRequests: 1 }})
    expect(w.find('WfParameter').at(0).prop('wfModuleStatus')).toEqual('busy')
    expect(w.find('StatusLine').prop('status')).toEqual('busy')
    expect(w.prop('className')).toMatch(/\bstatus-busy\b/)
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
        loadurl: {
          name: 'Load from URL',
          id_name: 'loadurl',
          help_url: '',
          icon: 'icon',
          parameter_specs: []
        }
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
          wfModule={{ id: 20, module: 'loadurl', tab_id: 11, is_collapsed: false, status: 'error', params: {}, error: 'foo', quick_fixes: [{text: 'Fix', action: 'prependModule', args: ['fixtype', {foo: 'bar'}]}] }}
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
    expect(mockApi.addModule).toHaveBeenCalledWith(11, 'fixtype', 1, {foo: 'bar'})
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
          999: { module: 'loadurl', params: {} }
        },
        modules: {
          'loadurl': {
            id_name: 'loadurl',
            name: 'Load from URL',
            help_url: '',
            icon: 'icon',
            parameter_specs: [ pspec('url', 'string') ]
          }
        },
        ...action.payload
      }))

      highlight([])

      wrapper = mount(
        <Provider store={store}>
          <ConnectedWfModule
            isReadOnly={false}
            isAnonymous={false}
            isZenMode={false}
            isZenModeAllowed={false}
            index={1}
            tabId={11}
            wfModule={{ id: 20, module: 'loadurl', tab_id: 11, is_collapsed: false, status: 'error', params: {}, error: 'foo', quick_fixes: [{text: 'Fix', action: 'prependModule', args: ['fixtype', {foo: 'bar'}]}] }}
            isSelected={true}
            isAfterSelected={false}
            onDragStart={jest.fn()}
            onDragEnd={jest.fn()}
            setZenMode={jest.fn()}
            api={mockApi}
          />
        </Provider>
      )
    })
    afterEach(() => {
      if (wrapper !== null) {
        wrapper.unmount()
        wrapper = null
      }
    })

    it('highlights a WfModule', () => {
      highlight([{ type: 'WfModule', index: 1, moduleName: 'Load from URL' }])
      expect(wrapper.find('.wf-module').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights a WfModule', () => {
      // wrong name
      highlight([{ type: 'WfModule', index: 1, moduleName: 'TestModule2' }])
      expect(wrapper.find('.wf-module').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the "collapse" button', () => {
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'Load from URL', button: 'collapse' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the "collapse" button', () => {
      // wrong moduleName
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'TestModule2', button: 'collapse' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).not.toMatch(/\blesson-highlight\b/)

      // wrong button
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'Load from URL', button: 'notes' }])
      expect(wrapper.find('i.context-collapse-button').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })

    it('highlights the notes button', () => {
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'Load from URL', button: 'notes' }])
      expect(wrapper.find('button.edit-note').prop('className')).toMatch(/\blesson-highlight\b/)
    })

    it('unhighlights the notes button', () => {
      // wrong moduleName
      highlight([{ type: 'WfModuleContextButton', index: 1, moduleName: 'TestModule2', button: 'notes' }])
      expect(wrapper.find('button.edit-note').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })
  })

  // Conditional UI tests
  describe('conditional parameter visibility', () => {
    // merge a visible_if block into the second parameter array of our test module
    const insertVisibleIf = (visibleIfTest) => {
      return {
        ...module,
        parameter_specs: [
          module.parameter_specs[0],
          {
            ...module.parameter_specs[1],
            visible_if: visibleIfTest
          },
          module.parameter_specs[2],
          module.parameter_specs[3],
          module.parameter_specs[4]
        ]
      }
    }

    // These depend on the test data
    const numModulesIfVisible = 4 // five params, one invisible by default
    const numModulesIfNotVisible = 3

    // These tests depend on there being a WfParameter id named menu_select that is set to "Banana"
    it('Conditional parameter visible via menu', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Banana"}'
      const w = wrapper({ module: insertVisibleIf(visibleIf) })
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })

    it('Conditional parameter not visible via menu', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Mango"}'
      const w = wrapper({ module: insertVisibleIf(visibleIf) })
      expect(w.find('WfParameter')).toHaveLength(numModulesIfNotVisible)
    })

    it('Conditional parameter not visible via inverted menu', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Banana", "invert":true}'
      const w = wrapper({ module: insertVisibleIf(visibleIf) })
      expect(w.find('WfParameter')).toHaveLength(numModulesIfNotVisible)
    })

    it('Conditional parameter visible via inverted menu', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Mango", "invert":true}'
      const w = wrapper({ module: insertVisibleIf(visibleIf) })
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })

    it('Conditional parameter visible via checkbox', () => {
      const visibleIf = '{"id_name":"some_boolean", "value":true}'
      const w = wrapper({ module: insertVisibleIf(visibleIf) })
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })

    it('Conditional parameter invisible via inverted checkbox', () => {
      const visibleIf = '{"id_name":"some_boolean", "value":true, "invert":true}'
      const w = wrapper({ module: insertVisibleIf(visibleIf) })
      expect(w.find('WfParameter')).toHaveLength(numModulesIfNotVisible)
    })

    it('Conditional parameter invisible via invisible parent', () => {
      // Even though the parent ("invisible_by_default" parameter) is set to the corrent menu item, it's not visible
      // So we shouldn't be either
      const visibleIf = '{"id_name":"invisible_by_default", "value":"Durian"}'
      const w = wrapper({ module: insertVisibleIf(visibleIf) })
      expect(w.find('WfParameter')).toHaveLength(numModulesIfNotVisible)
    })

    it('No infinite loop on parent name', () => {
      const visibleIf = '{"id_name":"menu_select", "value":"Banana"}'
      const w = wrapper({ module: insertVisibleIf(visibleIf) })
      expect(w.find('WfParameter')).toHaveLength(numModulesIfVisible)
    })
  })
})
