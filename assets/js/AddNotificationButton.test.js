/**
 * Testing Stories:
 * -Renders library-open version
 * -Renders library-closed version
 * -Either version can be dragged 
 * 
 */

import React from 'react'
import AddNotificationButton  from './AddNotificationButton'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('AddNotificationButton ', () => {

  var wrapper;  

  describe('Library Open ', () => {
  
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <AddNotificationButton
          libraryOpen={true}
        />
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
      expect( Object.keys(wrapper.find('AddNotificationButton').props()).includes('connectDragSource') ).toBe(true);
    });

  });

  describe('Library Closed ', () => {
    
    beforeEach(() => wrapper = mount(
      <DragDropContextProvider backend={HTML5Backend}>
        <AddNotificationButton
          libraryOpen={false}
        />
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
      expect( Object.keys(wrapper.find('AddNotificationButton').props()).includes('connectDragSource') ).toBe(true);
    });
  });

});
