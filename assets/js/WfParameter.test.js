jest.mock('./lessons/lessonSelector', () => jest.fn()) // same mock in every test :( ... we'll live

import React from 'react'
import ConnectedWfParameter, { WfParameter } from './WfParameter'
import { shallow, mount } from 'enzyme'
import { createStore } from 'redux'
import { Provider } from 'react-redux'
import lessonSelector from './lessons/lessonSelector'

describe('WfParameter', () => {

  var nullApi = {};
  var nullFn = () => {};

  // For testing conditional UI
  var mockGetParamMenuItems = (param_id) => {return 'Sugar|Butter||Flour'.split('|').map(s => s.trim())}
  var visibilityCond1 = {
    'id_name': 'whatever',
    'value': 'Butter|Flour'
  };
  var visibilityCond2 = {
    'id_name': 'whatever',
    'value': 'Sugar',
  };
  var visibilityCond3 = {
    'id_name': 'whatever',
    'value': true,
  };

  function shallowParameter(p, paramtextReturnValue) {
    return shallow(
      <WfParameter
        p={p}
        moduleName="test"
        wf_module_id={0}
        revision={0}
        loggedInUser={{}}
        api={nullApi}
        changeParam={nullFn}
        getParamText={(id) => paramtextReturnValue}
        setParamText={nullFn}
        getParamMenuItems={mockGetParamMenuItems}
        startDrag={nullFn}
        stopDrag={nullFn}        
        isLessonHighlight={false}
      />);
  }

  it('Renders cell editor', () => {
    var wrapper = shallowParameter({visible: true, value: '', parameter_spec: {type:'custom', id_name:'celledits' }});
    expect(wrapper.find('CellEditor')).toHaveLength(1);
    expect(wrapper).toMatchSnapshot();
  });

  it('Renders string input field', () => {
    var wrapper = shallowParameter({visible: true, value: 'data.sfgov.org', parameter_spec: {type:'string', id_name:'url'}});
    expect(wrapper.find('textarea')).toHaveLength(1);
    expect(wrapper).toMatchSnapshot();
  });

  // Conditional UI tests

  it('Renders a parameter when visible_if conditions are met', () => {
    var wrapper = shallowParameter({
        visible: true,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond1),
        }
    }, 3);
    expect(wrapper.find('textarea')).toHaveLength(1);
  });

  it('Does not render a parameter when visible_if conditions are not met', () => {
    var wrapper = shallowParameter({
        visible: true,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond2),
        }
    }, 3);
    expect(wrapper.find('textarea')).toHaveLength(0);
  });

  it('Does not render a parameter when visible_if conditions are met but visible_if is inverted', () => {
      var newVisibilityCond = Object.assign(visibilityCond1, {});
      newVisibilityCond['invert'] = true;
      var wrapper = shallowParameter({
        visible: true,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(newVisibilityCond),
        }
    }, 3);
    expect(wrapper.find('textarea')).toHaveLength(0);
  });

  it('Renders a parameter when visible_if conditions are not met but visible_if is inverted', () => {
      var newVisibilityCond = Object.assign(visibilityCond2, {});
      newVisibilityCond['invert'] = true;
      var wrapper = shallowParameter({
        visible: true,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(newVisibilityCond),
        }
    }, 3);
    expect(wrapper.find('textarea')).toHaveLength(1);
  });

  it('Renders a parameter when boolean visible_if conditions are met', () => {
      var wrapper = shallowParameter({
        visible: true,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond3),
        }
    }, true);
    expect(wrapper.find('textarea')).toHaveLength(1);
  });

  it('It does not render a parameter when boolean visible_if conditions are not met', () => {
      var wrapper = shallowParameter({
        visible: true,
        value: 'data.sfgov.org',
        parameter_spec: {
          id_name: 'url',
          type: 'string',
          visible_if: JSON.stringify(visibilityCond3),
        }
    }, false);
    expect(wrapper.find('textarea')).toHaveLength(0);
  });

  describe('lesson highlights', () => {
    let store
    let wrapper = null
    let nonce = 0

    function highlight(moduleName=null, name=null) {
      lessonSelector.mockReturnValue({
        testHighlight: test => {
          return test.type === 'WfParameter' && test.moduleName === moduleName && test.name === name
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

      wrapper = null // highlight() reads it
      highlight(null)
    })
    afterEach(() => {
      wrapper.unmount()
    })

    function wrap(p) {
      wrapper = mount(
        <Provider store={store}>
          <ConnectedWfParameter
            p={Object.assign({ visible: true }, p)}
            moduleName="test"
            wf_module_id={0}
            revision={0}
            loggedInUser={{}}
            api={{}}
            changeParam={jest.fn()}
            getParamText={(id) => paramtextReturnValue}
            setParamText={jest.fn()}
            getParamMenuItems={mockGetParamMenuItems}
            startDrag={jest.fn()}
            stopDrag={jest.fn()}        
            />
        </Provider>
      )
    }

    it('should highlight and unhighlight', () => {
      wrap({ parameter_spec: { id_name: 'url', type: 'string', name: 'URL' }})
      highlight('test', 'url')
      console.log(wrapper.html())
      expect(wrapper.find('.wf-parameter').prop('className')).toMatch(/\blesson-highlight\b/)
      highlight('test', 'anything_but_url')
      expect(wrapper.find('.wf-parameter').prop('className')).not.toMatch(/\blesson-highlight\b/)
    })
  })
});

