/**
 * Testing Stories:
 * -Renders a Module card, with icon received from props
 * -Drag feature works ( details TBD)
 */

import React from 'react'
import Module  from './Module'
import { mount, shallow } from 'enzyme'
// import { jsonResponseMock, emptyAPI } from './utils'
import HTML5Backend from 'react-dnd-html5-backend'
import { DragDropContextProvider } from 'react-dnd'


describe('Module ', () => {
  
  var wrapper;  

  beforeEach(() => wrapper = mount(
    <DragDropContextProvider backend={HTML5Backend}>
      <Module
        name={"Sweet Module"}
        icon={"add"}
        id={88}
        addModule={() => {}}
        dropModule={() => {}}
      />
    </DragDropContextProvider>
  ));

  it('Renders a card, with icon received from props', () => { 
    expect(wrapper).toMatchSnapshot();
  });

  // it('Card can be dragged and added to module stack', () => { 
  //   expect(true).toBe(true);
  // });
    
});