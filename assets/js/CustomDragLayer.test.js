import React from 'react'
import {shallow} from "enzyme/build/index";
import { CustomDragLayer } from "./CustomDragLayer";

describe('Custom drag layer (rendered)', () => {

  let wrapper;

  beforeEach(() => wrapper = shallow(
    <CustomDragLayer
      isDragging={true}
      itemType="module"
      item={{
        name:"Some Module",
        icon:"some-icon"
      }}
      getSourceClientOffset={{
        x:10,
        y:10
      }}
    />
  ));

  it('Renders the drag layer', () => {
    expect(wrapper).toMatchSnapshot();
    let innerDiv = wrapper.find('div');
    expect(innerDiv.get(1).props.style).toHaveProperty('transform','translate3d(10px, 10px, 0)');
  });

});

describe('Custom drag layer (not rendered)', () => {

  let wrapper;

  beforeEach(() => wrapper = shallow(
    <CustomDragLayer
      isDragging={false}
      itemType={null}
      item={null}
      getSourceClientOffset={null}
    />
  ));

  it('Renders the drag layer', () => {
    expect(wrapper).toMatchSnapshot();
    let innerDiv = wrapper.find('div');
    expect(innerDiv.get(1).props.style).toHaveProperty('display','none');
  });

});
