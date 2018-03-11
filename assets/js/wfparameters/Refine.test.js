import React from 'react'
import Refine, {EditRow, mockAPI} from './Refine'
import {mockStore} from '../workflow-reducer'
import {jsonResponseMock} from '../utils'
import {mount} from 'enzyme'

describe('Refine', () => {

    var store, api;
    var wrapper;

    // Mocks response to the histogram API call
    const histogramResponse = {
        columns: ['foo', 'count'],
        start_row: 0,
        end_row: 3,
        total_rows: 3,
        rows: [
            {foo: 'bar1', count: 1},
            {foo: 'bar2', count: 2},
            {foo: 'bar3', count: 3}
        ]
    };

    var existingEdits = '[]';

    function mockSaveEdits(edits) {
        //console.log('mockSaveEdits called');
        existingEdits = edits;
    }

    mockSaveEdits = mockSaveEdits.bind(this);

    beforeEach(() => {
        existingEdits = '[]';

        api = {
           onParamChanged: jest.fn().mockReturnValue(Promise.resolve()),
           histogram: jsonResponseMock(histogramResponse)
        };
        mockAPI(api);
        /*
        store = {
           getState: () => initialState,
           dispatch: jest.fn()
        };
        mockStore(store);
        */
        wrapper = mount(
            <Refine
               wfModuleId={101}
               selectedColumn={'foo'}
               existingEdits={existingEdits}
               saveEdits={mockSaveEdits}
               revision={0}
            />
        )
    });

    it('loads the histogram', (done) => {
        //expect(wrapper).toMatchSnapshot();

        setImmediate(() => {
            expect(wrapper.state()).toEqual({
                histogramLoaded: true,
                histogramNumRows: histogramResponse.total_rows,
                histogramData: histogramResponse.rows.map(function(entry) {
                    var newEntry = Object.assign({}, entry);
                    newEntry.selected = true;
                    newEntry.edited = false;
                    return newEntry;
                }).sort((item1, item2) => {
                    return (item1.count < item2.count ? 1 : -1);
                }),
                showWarning: false,
                edits: []
            });
            done();
        });
    });

    it('updates the histogram upon value edit', (done) => {
        setImmediate(() => {
            var bar1Input = wrapper.find('input[value="bar1"]');
            expect(bar1Input).toHaveLength(1);

            bar1Input.simulate('focus');
            bar1Input.simulate('change', {
                target: {
                    value: 'bar2'
                }
            });
            bar1Input.simulate('keyPress', {
                key: 'Enter'
            });

            setImmediate(() => {

                wrapper.setProps({
                    existingEdits: existingEdits,
                    revision: 1
                })

                setImmediate(() => {
                    //console.log(wrapper.state().histogramData);
                    expect(wrapper.state().histogramData).toEqual(
                        [
                            {foo: 'bar2', count: 3, selected: true, edited: true},
                            {foo: 'bar3', count: 3, selected: true, edited: false}
                        ]
                    );
                    expect(wrapper.find('EditRow')).toHaveLength(2);

                    done();
                });

            });

        });
    });
});