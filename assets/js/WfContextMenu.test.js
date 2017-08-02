import React from 'react'
import WfContextMenu  from './WfContextMenu'
import { mount } from 'enzyme'


it('WfContextMenu renders correctly', () => {
  const wrapper = mount(
    <WfContextMenu removeModule={ () => {} } />
  );
  expect(wrapper).toMatchSnapshot();
});





