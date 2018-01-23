/**
 * Testing Stories:
 * -Renders card
 * -Card can be dragged 
 * 
 */

import React from 'react'
import AddNotificationButtonOpen  from './AddNotificationButtonOpen'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('AddNotificationButtonOpen ', () => {

  var wrapper;  

  beforeEach(() => wrapper = mount(
    <DragDropContextProvider backend={HTML5Backend}>
      <AddNotificationButtonOpen/>
    </DragDropContextProvider>
  ));
  afterEach(() => wrapper.unmount());    

  it('Renders', () => { 
    expect(wrapper).toMatchSnapshot();
    // find matching icon
    expect(wrapper.find('.icon-notification')).toHaveLength(1);
  });

  it('Card is draggable', () => { 
    // search for property on the component that indicates drag-ability
    expect( Object.keys(wrapper.find('AddNotificationButtonOpen').props()).includes('connectDragSource') ).toBe(true);
  });

});
