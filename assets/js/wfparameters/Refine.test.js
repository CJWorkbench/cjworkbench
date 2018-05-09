import React from 'react'
import Refine, {EditRow, mockAPI} from './Refine'
import {mockStore} from '../workflow-reducer'
import {jsonResponseMock} from '../utils'
import {mount} from 'enzyme'

describe('Refine', () => {

    const INTERNAL_COUNT_COLNAME = '__internal_count_column__'

    let store, api, wrapper

    // Mocks response to the histogram API call
    const histogramResponse = {
        columns: ['foo', 'count'],
        start_row: 0,
        end_row: 3,
        total_rows: 3,
        rows: [
            {foo: 'bar1', '__internal_count_column__': 1},
            {foo: 'bar2', '__internal_count_column__': 2},
            {foo: 'bar3', '__internal_count_column__': 3}
        ]
    };

    let existingEdits = '[]';

    function mockSaveEdits(edits) {
        //console.log('mockSaveEdits called');
        existingEdits = edits;
    }

    beforeEach(() => {
        existingEdits = '[]';

        api = {
           onParamChanged: jest.fn().mockReturnValue(Promise.resolve()),
           histogram: jsonResponseMock(histogramResponse)
        };
        mockAPI(api);
        wrapper = mount(
            <Refine
               wfModuleId={101}
               selectedColumn={'foo'}
               existingEdits={existingEdits}
               saveEdits={mockSaveEdits}
               revision={0}
            />
        )
    })

    afterEach(() => wrapper.unmount())

    it('loads the histogram', (done) => {
        //expect(wrapper).toMatchSnapshot();

        setImmediate(() => {
            wrapper.update()
            expect(wrapper.state()).toEqual({
                selectedColumn: 'foo',
                histogramLoaded: true,
                histogramNumRows: histogramResponse.total_rows,
                histogramData: histogramResponse.rows.map(function(entry) {
                    var newEntry = Object.assign({}, entry);
                    newEntry.selected = true;
                    newEntry.edited = false;
                    return newEntry;
                }).sort((item1, item2) => {
                    return (item1[INTERNAL_COUNT_COLNAME] < item2[INTERNAL_COUNT_COLNAME] ? 1 : -1);
                }),
                showWarning: false,
                showColError: false,
                edits: [],
            });
            done();
        });
    });

    it('updates the histogram upon value edit', (done) => {
        setImmediate(() => {
            wrapper.update()
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
                wrapper.update()
                wrapper.setProps({
                    existingEdits: existingEdits,
                    revision: 1
                });

                setImmediate(() => {
                    wrapper.update()
                    //console.log(wrapper.state().histogramData);
                    expect(wrapper.state().histogramData).toEqual(
                        [
                            {foo: 'bar2', '__internal_count_column__': 3, selected: true, edited: true},
                            {foo: 'bar3', '__internal_count_column__': 3, selected: true, edited: false}
                        ]
                    );
                    expect(wrapper.find('EditRow')).toHaveLength(2);

                    done();
                });

            });

        });
    });

    it('updates the checkboxes upon value (de)selection', (done) => {
      const findBar1Checkbox = (name) => {
        return wrapper.find('EditRow').at(0).find('input[type="checkbox"]')
      }

        setImmediate(() => {
            wrapper.update()
            // Click the checkbox for value 'bar1'

            expect(findBar1Checkbox().prop('checked')).toBe(true)
            findBar1Checkbox().simulate('change')

            // Update the component
            wrapper.setProps({
                existingEdits: existingEdits,
                revision: 1
            })

            setImmediate(() => {
                wrapper.update()
                // And check that the checkbox should not be checked
                // After that, click the checkbox again

                expect(findBar1Checkbox().prop('checked')).toBe(false)
                findBar1Checkbox().simulate('change');

                // Update the component
                wrapper.setProps({
                    existingEdits: existingEdits,
                    revision: 2
                })

                setImmediate(() => {
                    wrapper.update()
                    // And check that the checkbox should be checked now

                    expect(findBar1Checkbox().prop('checked')).toBe(true)

                    done();
                });
            });
        });
    })
});
