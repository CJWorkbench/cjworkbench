/**
 * Testing Stories:
 * -Renders a Module card, with icon received from props
 * -Draggable feature exists
 * -Read-only version will collapse parent category on click
 * 
 */

import React from 'react'
import Module  from './Module'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('Module', () => {
  
  var wrapper;
  var setOpenCategory;
  var addModule;

  describe('NOT Read-only', () => {
  
    beforeEach(() => {
      setOpenCategory = jest.fn();
      addModule = jest.fn();
      wrapper = mount(
        <DragDropContextProvider backend={HTML5Backend}>
          <Module
            key={"Sweet Module"}
            name={"Sweet Module"}
            icon={"add"}
            id={88}
            addModule={addModule}
            dropModule={() => {}}
            isReadOnly={false} 
            setOpenCategory={setOpenCategory}           
          />
        </DragDropContextProvider>
      )
    });
    afterEach(() => wrapper.unmount());

    it('Renders a card, with icon received from props', () => { 
      expect(wrapper).toMatchSnapshot();
      expect(wrapper.find('.icon-add')).toHaveLength(1);
    });

    it('Card is draggable', () => { 
      // find property on the Module component that indicates drag-ability
      expect( Object.keys(wrapper.find('Module').props()).includes('connectDragSource') ).toBe(true);
    });

    it('Clicking on card will call function to add module', () => { 
      let card = wrapper.find('.ml-module-card');
      expect(card).toHaveLength(1);
      card.simulate('click');
      expect(addModule.mock.calls.length).toBe(1); 
    });

  });


  describe('Read-only', () => {
  
    beforeEach(() => {
      setOpenCategory = jest.fn();
      addModule = jest.fn();      
      wrapper = mount(
        <DragDropContextProvider backend={HTML5Backend}>
          <Module
            key={"Sweet Module"}
            name={"Sweet Module"}
            icon={"add"}
            id={88}
            addModule={addModule}
            dropModule={() => {}}
            isReadOnly={true} 
            setOpenCategory={setOpenCategory}           
          />
        </DragDropContextProvider>
      )
    });
    afterEach(() => wrapper.unmount());

    it('Renders a card, with icon received from props', () => { 
      expect(wrapper).toMatchSnapshot();
      expect(wrapper.find('.icon-add')).toHaveLength(1);
    });

    it('Clicking on card will call function to collapse its category', () => { 
      let card = wrapper.find('.ml-module-card');
      expect(card).toHaveLength(1);
      card.simulate('click');
      expect(setOpenCategory.mock.calls.length).toBe(1); 
    });

  });
  
    
});