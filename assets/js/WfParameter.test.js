import React from 'react'
import WfParameter from './WfParameter'
import { shallow } from 'enzyme'

describe('WfParameter', () => {

  var nullApi = {};
  var nullFn = () => {};

  function shallowParameter(p) {
    return shallow(
      <WfParameter
        p={p}
        wf_module_id={0}
        revision={0}
        loggedInUser={{}}
        api={nullApi}
        changeParam={nullFn}
	      getParamText={nullFn}
	      setParamText={nullFn}
      />);
  }

  it('Renders cell editor', () => {
    var wrapper = shallowParameter({visible: true, value: '', parameter_spec: {type:'custom', id_name:'celledits' }});
    expect(wrapper.find('CellEditor')).toHaveLength(1);
    expect(wrapper).toMatchSnapshot();
  });

});

