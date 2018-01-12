import React from 'react'
import WorkbenchAceEditor  from './AceEditor'
import { mount, ReactWrapper } from 'enzyme'
import AceEditor from 'react-ace';

// This is a dumb test, we can't test the blur or
// change events and I can't nail down why yet
describe('AceEditor', () => {
  it('Mounts correctly and saves on blur', (done) => {
    var mockOnSave = jest.fn();
    var wrapper = mount(<WorkbenchAceEditor
      name="def process(table)"
      defaultValue="return table"
      onSave={(val) => {mockOnSave(val)}}
    />);
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.state().value).toBe('return table');
    done();
  });
});
