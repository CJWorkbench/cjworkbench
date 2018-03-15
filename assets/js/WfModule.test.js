import React from 'react'
import { WfModule } from './WfModule'
import { shallow } from 'enzyme'

describe('WfModule, NOT read-only mode - DUMMY TEST ONLY', () => {

  var wrapper;
  var props = {
        'data-isReadOnly': false,
        'data-wfmodule': {
          'notes': [],
          'parameter_vals': [],
          'module_version': {
            'module': {},
          }
        },
        'data-changeParam': () => {} ,
        'data-removeModule':  () => {} ,
        'data-revision': 707,
        'data-selected': false,
        'data-api': {},
        'connectDragSource': (component) => {return component},
        'connectDropTarget': (component) => {return component},
        'focusModule': () => {}
      };

  beforeEach(() => {
    wrapper = shallow(
      <WfModule
        {...props}
      />
    )
  });

  it('Renders - dummy test only', () => {
    expect(wrapper).toMatchSnapshot();
  });

});
