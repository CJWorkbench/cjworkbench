import React from 'react'
import ReorderHistory from './ReorderHistory'
import {shallow} from 'enzyme'


describe('ReorderHistory rendering', () => {
    it('Renders with empty history', () => {
       let tree = shallow(<ReorderHistory history={''}/>)
       expect(tree.find('.reorder-idx')).toHaveLength(0);
       expect(tree.find('.reorder-column')).toHaveLength(0);
       expect(tree.find('.reorder-from')).toHaveLength(0);
       expect(tree.find('.reorder-to')).toHaveLength(0);
    });

    it('Renders history properly', () => {
        let history = [
            {
                'column': 'maze',
                'from': 0, // A
                'to': 2 // C
            },
            {
                'column': 'door',
                'from': 26, // AA
                'to': 1 // B
            }
        ];
        let tree = shallow(<ReorderHistory history={JSON.stringify(history)}/>)
        expect(tree.find('.reorder-idx')).toHaveLength(2);
        expect(parseInt(tree.find('.reorder-idx').get(0).props.children)).toEqual(1);
        expect(parseInt(tree.find('.reorder-idx').get(1).props.children)).toEqual(2);

        expect(tree.find('.reorder-column')).toHaveLength(2);
        expect(tree.find('.reorder-column').get(0).props.children).toEqual('maze');
        expect(tree.find('.reorder-column').get(1).props.children).toEqual('door');

        expect(tree.find('.reorder-from')).toHaveLength(2);
        expect(tree.find('.reorder-from').get(0).props.children).toEqual('A');
        expect(tree.find('.reorder-from').get(1).props.children).toEqual('AA');

        expect(tree.find('.reorder-to')).toHaveLength(2);
        expect(tree.find('.reorder-to').get(0).props.children).toEqual('C');
        expect(tree.find('.reorder-to').get(1).props.children).toEqual('B');
    });
})