import {updateSort, mockAPI} from "./SortFromTable";
import {mockStore, mockAPI as mockStoreApi} from './workflow-reducer'
import { jsonResponseMock } from './utils'

describe("SortFromTable actions", () => {
   var store, api;

   // A few parameter id constants for better readability
   const COLUMN_PAR_ID_1 = 35;
   const DTYPE_PAR_ID_1 = 85;
   const DIRECTION_PAR_ID_1 = 135;

   const COLUMN_PAR_ID_2 = 70;
   const DTYPE_PAR_ID_2 = 170;
   const DIRECTION_PAR_ID_2 = 270;

   const COLUMN_PAR_ID_3 = 140;
   const DTYPE_PAR_ID_3 = 340;
   const DIRECTION_PAR_ID_3 = 540;

   var initialState = {
       sortModuleId: 77,
       workflow: {
           id: 127,
           wf_modules: [
               {
                   id: 17,
                   module_version: {
                       module: {
                           id_name: 'loadurl'
                       }
                   }
               },
               {
                   // An existing sort module
                   id: 7,
                   module_version: {
                       module: {
                           id_name: 'sort-from-table'
                       }
                   },
                   parameter_vals: [
                       {
                           id: COLUMN_PAR_ID_2,
                           parameter_spec: {id_name: 'column'},
                           value: ''
                       },
                       {
                           id: DTYPE_PAR_ID_2,
                           parameter_spec: {id_name: 'dtype'},
                           value: 0   // String
                       },
                       {
                           id: DIRECTION_PAR_ID_2,
                           parameter_spec: {id_name: 'direction'},
                           value: 0     // Select
                       }
                   ]
               },
               {
                   id: 19,
                   module_version: {
                       module: {
                           id_name: 'colselect'
                       }
                   }
               },
               {
                   id: 31,
                   module_version: {
                       module: {
                           id_name: 'filter'
                       }
                   }
               },
               {
                   // Another existing sort module, set to num_col descending
                   id: 79,
                   module_version: {
                       module: {
                           id_name: 'sort-from-table'
                       }
                   },
                   parameter_vals: [
                       {
                           id: COLUMN_PAR_ID_3,
                           parameter_spec: {id_name: 'column'},
                           value: 'num_col'
                       },
                       {
                           id: DTYPE_PAR_ID_3,
                           parameter_spec: {id_name: 'dtype'},
                           value: 1   // Number
                       },
                       {
                           id: DIRECTION_PAR_ID_3,
                           parameter_spec: {id_name: 'direction'},
                           value: 2   // Descending
                       }
                   ]
               }
           ]
       }
   };

   const addModuleResponse = {
       id: 23,
       module_version: {
           module: {
               id_name: 'sort-from-table'
           }
       },
       parameter_vals: [
           {
               id: COLUMN_PAR_ID_1,
               parameter_spec: {id_name: 'column'},
               value: ''
           },
           {
               id: DTYPE_PAR_ID_1,
               parameter_spec: {id_name: 'dtype'},
               value: 0,
           },
           {
               id: DIRECTION_PAR_ID_1,
               parameter_spec: {id_name: 'direction'},
               value: 0
           }
       ]
   };

   const columnsResponse = [
       {name: "num_col", type: "Number"},
       {name: "str_col", type: "String"},
       {name: "date_col", type: "Date"}
   ];

   beforeEach(() => {
       api = {
           onParamChanged: jest.fn().mockReturnValue(Promise.resolve()),
           addModule: jsonResponseMock(addModuleResponse),
           setSelectedWfModule: jest.fn().mockReturnValue(Promise.resolve()),
           getColumns: jsonResponseMock(columnsResponse)
       }
       mockAPI(api);
       mockStoreApi(api);
       store = {
           getState: () => initialState,
           dispatch: jest.fn().mockReturnValue(Promise.resolve())
       }
       mockStore(store)
   });

   it('Adds new sort module after the given module and sets sort parameters if one does not exist', (done) => {
      updateSort(19, 'num_col', 'Number');
      setImmediate(() => {
          // Checks the module adding part
          expect(api.addModule.mock.calls).toHaveLength(1);
          // sortModuleId
          expect(api.addModule.mock.calls[0][1]).toBe(initialState.sortModuleId);
          // sortModuleIdx, should be 3 since we are adding after the module with index 2
          expect(api.addModule.mock.calls[0][2]).toBe(3);

          // Checks the parameter setting part
          setImmediate(() => {
              // 3 calls as we are setting column, dtype and direction
              expect(api.onParamChanged.mock.calls).toHaveLength(3);

              // First call changes the column
              expect(api.onParamChanged.mock.calls[0][0]).toBe(COLUMN_PAR_ID_1);
              expect(api.onParamChanged.mock.calls[0][1].value).toBe('num_col');

              // Second call changes the dtype
              expect(api.onParamChanged.mock.calls[1][0]).toBe(DTYPE_PAR_ID_1);
              // 1 -> Number
              expect(api.onParamChanged.mock.calls[1][1].value).toBe(1);

              // Third call changes the direction
              expect(api.onParamChanged.mock.calls[2][0]).toBe(DIRECTION_PAR_ID_1);
              // 2 -> Descending (which is the default for numbers)
              expect(api.onParamChanged.mock.calls[2][1].value).toBe(2);

              done();
          });
      });
   });

   it('Updates the existing sort module after the current non-sort module correctly for a string column', (done) => {
       // Click on 'str_col' once, which should give us ascending order
       updateSort(17, 'str_col', 'String');
       setImmediate(() => {
           // 3 calls as we are setting column, dtype and direction
           expect(api.onParamChanged.mock.calls).toHaveLength(3);

           // First call changes the column
           expect(api.onParamChanged.mock.calls[0][0]).toBe(COLUMN_PAR_ID_2);
           expect(api.onParamChanged.mock.calls[0][1].value).toBe('str_col');

           // Second call changes the dtype
           expect(api.onParamChanged.mock.calls[1][0]).toBe(DTYPE_PAR_ID_2);
           // 0 -> String
           expect(api.onParamChanged.mock.calls[1][1].value).toBe(0);

           // Third call changes the direction
           expect(api.onParamChanged.mock.calls[2][0]).toBe(DIRECTION_PAR_ID_2);
           // 1 -> Ascending (which is the default for strings)
           expect(api.onParamChanged.mock.calls[2][1].value).toBe(1);

           done();
       });
   });

   it('Updates the existing sort module after the current non-sort module correctly for a number column', (done) => {
       // Click on 'num_col' once, which should give us descending order
       updateSort(17, 'num_col', 'Number');
       setImmediate(() => {
           // 3 calls as we are setting column, dtype and direction
           expect(api.onParamChanged.mock.calls).toHaveLength(3);

           // First call changes the column
           expect(api.onParamChanged.mock.calls[0][0]).toBe(COLUMN_PAR_ID_2);
           expect(api.onParamChanged.mock.calls[0][1].value).toBe('num_col');

           // Second call changes the dtype
           expect(api.onParamChanged.mock.calls[1][0]).toBe(DTYPE_PAR_ID_2);
           // 1 -> Number
           expect(api.onParamChanged.mock.calls[1][1].value).toBe(1);

           // Third call changes the direction
           expect(api.onParamChanged.mock.calls[2][0]).toBe(DIRECTION_PAR_ID_2);
           // 2 -> Descending (which is the default for numbers)
           expect(api.onParamChanged.mock.calls[2][1].value).toBe(2);

           done();
       });
   });

   it('Updates the existing sort module after the current non-sort module correctly for a date column', (done) => {
       // Click on 'date_col' once, which should give us descending order
       updateSort(17, 'date_col', 'Date');
       // We are using timeouts here as the function uses timeout to prevent database lock-up
       setImmediate(() => {
           // 3 calls as we are setting column, dtype and direction
           expect(api.onParamChanged.mock.calls).toHaveLength(3);

           // First call changes the column
           expect(api.onParamChanged.mock.calls[0][0]).toBe(COLUMN_PAR_ID_2);
           expect(api.onParamChanged.mock.calls[0][1].value).toBe('date_col');

           // Second call changes the dtype
           expect(api.onParamChanged.mock.calls[1][0]).toBe(DTYPE_PAR_ID_2);
           // 2 -> Date
           expect(api.onParamChanged.mock.calls[1][1].value).toBe(2);

           // Third call changes the direction
           expect(api.onParamChanged.mock.calls[2][0]).toBe(DIRECTION_PAR_ID_2);
           // 2 -> Descending (which is the default for numbers)
           expect(api.onParamChanged.mock.calls[2][1].value).toBe(2);

           done();
       });
   });

   it('Updates the current sort module correctly when sorted column header is clicked', (done) => {
       // Click on 'num_col' once, which should give us ascending order since previous is descending
       updateSort(79, 'num_col', 'Number');
       setImmediate(() => {
           // 1 call as we are only updating direction here
           expect(api.onParamChanged.mock.calls).toHaveLength(1);

           // First call changes the column
           expect(api.onParamChanged.mock.calls[0][0]).toBe(DIRECTION_PAR_ID_3);
           // 1 -> Ascending (since previous order is descending and this column is number)
           expect(api.onParamChanged.mock.calls[0][1].value).toBe(1);

           done();
       });
   });

   it('Updates the current sort module correctly when an unsorted header is clicked', (done) => {
       // Click on 'str_col' once, which should give us ascending order since previous is descending
       updateSort(79, 'str_col', 'String');
       setImmediate(() => {
           // 3 calls as we are setting column, dtype and direction
           expect(api.onParamChanged.mock.calls).toHaveLength(3);

           // First call changes the column
           expect(api.onParamChanged.mock.calls[0][0]).toBe(COLUMN_PAR_ID_3);
           expect(api.onParamChanged.mock.calls[0][1].value).toBe('str_col');

           // Second call changes the dtype
           expect(api.onParamChanged.mock.calls[1][0]).toBe(DTYPE_PAR_ID_3);
           // 0 -> String
           expect(api.onParamChanged.mock.calls[1][1].value).toBe(0);

           // Third call changes the direction
           expect(api.onParamChanged.mock.calls[2][0]).toBe(DIRECTION_PAR_ID_3);
           // 1 -> Ascending (which is the default for strings)
           expect(api.onParamChanged.mock.calls[2][1].value).toBe(1);

           done();
       });
   });
});