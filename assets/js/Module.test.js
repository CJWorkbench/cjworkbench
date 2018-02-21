/**
 * Testing Stories:
 * -Renders a Module card, with icon received from props
 * -Draggable feature exists
 * 
 * TODO:
 * 
 * -Not-read-only: calls AddModule from API on click
 * 
 * -Read-only state:
 *    -is not draggable
 *    -does not call AddModule
 * 
 */

import React from 'react'
import Module  from './Module'
import { mount } from 'enzyme'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('Module ', () => {
  
  var wrapper;  

  beforeEach(() => wrapper = mount(
    <DragDropContextProvider backend={HTML5Backend}>
      <Module
        key={"Sweet Module"}
        name={"Sweet Module"}
        icon={"add"}
        id={88}
        addModule={() => {}}
        dropModule={() => {}}
      />
    </DragDropContextProvider>
  ));
  afterEach(() => wrapper.unmount());

  it('Renders a card, with icon received from props', () => { 
    expect(wrapper).toMatchSnapshot();
    expect(wrapper.find('.icon-add')).toHaveLength(1);
  });

  it('Card is draggable', () => { 
    // search for property on the Module component that indicates drag-ability
    expect( Object.keys(wrapper.find('Module').props()).includes('connectDragSource') ).toBe(true);
  });
    
});