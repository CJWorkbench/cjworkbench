/**
 * Testing Stories:
 * -Renders library-open version
 * -Renders library-closed version
 * -Either version can be dragged to a data source module, which successfully adds alert
 * -Drag & drop to anything else does nothing
 */

import React from 'react'
import AddNotificationButton  from './AddNotificationButton'
import { mount, shallow } from 'enzyme'
// import { jsonResponseMock, emptyAPI } from './utils'
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

    it('Renders', () => { 
      expect(wrapper).toMatchSnapshot();
    });

    // Issue: "Cannot have two HTML5 backends at the same time" - how to do multiple tests?

    // it('Dragging icon to a data source will add an alert', () => { 
    //   expect(true).toBe(true);
    // });

    // it('Dragging icon to non data source will have no effect', () => { 
    //   expect(true).toBe(true);
    // });
  });

  // describe('Library Closed ', () => {
    
  //   beforeEach(() => wrapper = mount(
  //     <DragDropContextProvider backend={HTML5Backend}>
  //       <AddNotificationButton
  //         libraryOpen={false}
  //       />
  //     </DragDropContextProvider>
  //   ));

  //   it('Renders', () => { 
  //     expect(wrapper).toMatchSnapshot();
  //   });

  //   it('Dragging icon to a data source will add an alert', () => { 
  //     expect(true).toBe(true);
  //   });

  //   it('Dragging icon to non data source will have no effect', () => { 
  //     expect(true).toBe(true);
  //   });
  // });

});
