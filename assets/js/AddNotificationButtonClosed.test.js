/**
 * Testing Stories:
 * -Renders icon
 * -Mouse events on icon will show/hide full card
 * -Icon and card can be dragged
 *
 */

import React from 'react'
import AddNotificationButtonClosed  from './AddNotificationButtonClosed'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('AddNotificationButtonOpen ', () => {

  var wrapper;
  var setOpenCategory = () => {};

  beforeEach(() => wrapper = mount(
    <DragDropContextProvider backend={HTML5Backend}>
      <AddNotificationButtonClosed setOpenCategory={setOpenCategory}/>
    </DragDropContextProvider>
  ));
  afterEach(() => wrapper.unmount());

  it('Renders', () => {
    expect(wrapper).toMatchSnapshot();
    // find matching icon
    expect(wrapper.find('.icon-notification')).toHaveLength(1);
  });

  it('Mouse events on icon will show/hide full card', () => {
    let icon = wrapper.find('.notification-button-closed');
    let popout = wrapper.find('.alert-closed-ML');
    // check that card not displayed initially (governed by 'display' property)
    expect(popout.props().style).toEqual({display:'none'});
    // simulate mouse enter
    icon.simulate('mouseEnter');
    // look for card display
    expect(popout.props().style).toEqual({display:'block'});
    // simulate mouse leave
    icon.simulate('mouseLeave');
    // check that card not displayed again
    expect(popout.props().style).toEqual({display:'none'});
  });

  it('Card is draggable', () => {
    // search for property on the component that indicates drag-ability
    expect( Object.keys(wrapper.find('AddNotificationButtonClosed').props()).includes('connectDragSource') ).toBe(true);
  });


});
