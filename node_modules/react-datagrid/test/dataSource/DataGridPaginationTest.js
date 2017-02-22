'use strict';

var DataGrid  = require('../DataGrid')
var React     = require('react/addons')
var TestUtils = React.addons.TestUtils

var TABLE_CLASS          = 'z-table'
var ROW_CLASS            = 'z-row'
var CELL_CLASS           = 'z-cell'
var CELL_TEXT_CLASS      = 'z-text'

var REMOTE_DATA          = 'http://localhost:8090/10'
var REMOTE_DATA_OPTIONS  = '?pageSize=20&page=1&skip=0'
var REMOTE_DATA_OPTIONS2 = '?pageSize=1&page=1&skip=0'
var REMOTE_DATA_OPTIONS3 = '?pageSize=1&page=2&skip=1'

var PAGINATION_TOOLBAR   = 'react-datagrid-pagination-toolbar'
var PAGINATION_NEXT      = 'gotoNext'
var PAGINATION_PREV      = 'gotoPrev'

var testUtils = require('../utils')

var render        = testUtils.render
var findWithClass = testUtils.findWithClass
var tryWithClass  = testUtils.tryWithClass
var generateMockData = testUtils.generateMockData

var paginationEnabled
var remoteDataOptions = REMOTE_DATA_OPTIONS

// create mock fetchData

var fetchData = function(url) {
    // check url request is ok
    if(paginationEnabled){
        url.should.be.equal(REMOTE_DATA + remoteDataOptions);
    } else {
        url.should.be.equal(REMOTE_DATA);
    }

    var data = generateMockData({type : 'remote',len : 1})

    return new Promise(function(resolve,reject) {
        resolve(data)
    })
}

var columns = [
    { name: 'index', title: '#', width: 50 },
    { name: 'firstName'},
    { name: 'lastName'  },
    { name: 'city' },
    { name: 'email' }
]

describe('DataGrid Test Suite - Pagination', function(){


	it('check pagination toolbar visible when dataSource is remote ', function(done) {


        // flag to test pagination url in fetch
        paginationEnabled = true;

		// table
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: REMOTE_DATA,
                columns   : columns,
                style     : {height: 200},
                fetch     : fetchData
            })
        );

        // set time to resolve promise and render table
        setTimeout(function() {
            findWithClass(table,PAGINATION_TOOLBAR)
                .should.not.be.empty
            done()
        }, 0)

	})

	it('check pagination toolbar not visible by options ',function(done) {


		// flag to test pagination url in fetch
        paginationEnabled = false;

		// table
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: REMOTE_DATA,
                columns   : columns,
                style     : {height: 200},
                fetch     : fetchData,
                pagination: false
            })
        );

        // set time to resolve promise and render table
        setTimeout(function() {
            var paginationToolbar = tryWithClass(table, PAGINATION_TOOLBAR)
            paginationToolbar.should.be.empty
            done()
        },0)
	})

	it('check pagination works when dataSource is remote ',function(done) {

        // create dataSource
        var dataSource = function(request) {

            var data = generateMockData({type : 'remote', len : 3, request : request})

            return new Promise(function(resolve,reject) {
                resolve(data)
            })
        }

		// table first page render
        var table = render(
            DataGrid({
                idProperty		: 'id',
                dataSource 		: dataSource,
                columns   		: columns,
                style     		: {height:200},
                defaultPageSize : 2
            })
        );

        // set time to resolve promise and render table
        setTimeout(function() {

            var paginationToolbar = tryWithClass(table,PAGINATION_TOOLBAR)
            paginationToolbar.should.not.be.empty

            var rows = tryWithClass(table,ROW_CLASS)

            // check the number of rows
            rows.length.should.equal(2)

            // first, navigate to second page
            var nextPageButton = TestUtils.findAllInRenderedTree(table,function(node) {
                return node.props.name == PAGINATION_NEXT;
	        })[0];

            // click next page button
            TestUtils.Simulate.click(nextPageButton.getDOMNode());

            // set time to resolve promise and render table
            setTimeout(function() {

                // check next page content

                rows = tryWithClass(table,ROW_CLASS)
                rows.length.should.equal(1)

                // then navigate back to first page

                var prevPageButton = TestUtils.findAllInRenderedTree(table,function(node) {
                    return node.props.name == PAGINATION_PREV;
                })[0];
                // click previous page button
                TestUtils.Simulate.click(prevPageButton.getDOMNode())

                // set time to resolve promise and render table
                setTimeout(function() {

                    // check first page content again

                    rows = tryWithClass(table,ROW_CLASS)
                	rows.length.should.equal(2)

                    done()

                },0)

            },0)

        },0)

	})

    it('check pageSize prop ',function(done) {

        var PAGE_SIZE = 3

        // create dataSource
        var dataSource = function(request) {

            var data = generateMockData({type : 'remote', len : 4, request : request});

            var promise = new Promise(function(resolve,reject) {
                resolve(data)
            })
            return promise;
        };

        // table first page render
        var table = render(
            DataGrid({
                idProperty      : 'id',
                dataSource      : dataSource,
                columns         : columns,
                style           : {height:200},
                pageSize        : PAGE_SIZE
            })
        );

        setTimeout(function() {
            var rows = tryWithClass(table,ROW_CLASS)
            rows.length.should.equal(PAGE_SIZE)
            done()
        },0)

    })

    xit('check pageSizeChanged prop ',function(done) {

        var PAGE_SIZE = 3
        var CHANGED_PAGE_SIZE = 20

        // create dataSource
        var dataSource = function(request) {

            var data = generateMockData({type : 'remote', len : 4, request : request});

            var promise = new Promise(function(resolve,reject) {
                resolve(data)
            })
            return promise;
        };

        var onPageSizeChangeHandler = function(pageSize,props) {
            pageSize.should.equal(CHANGED_PAGE_SIZE)
        }

        // table first page render
        var table = render(
            DataGrid({
                idProperty      : 'id',
                dataSource      : dataSource,
                columns         : columns,
                style           : {height:200},
                pageSize        : PAGE_SIZE,
                onPageSizeChange: onPageSizeChangeHandler
            })
        );

        setTimeout(function() {
            var paginationToolbar = findWithClass(table,PAGINATION_TOOLBAR)
            var selectPages =  TestUtils.findRenderedDOMComponentWithTag(paginationToolbar, 'select')
            TestUtils.Simulate.change(selectPages,{target : {value : CHANGED_PAGE_SIZE}})
            done()
        },0)

    })

    it('check page and onPageChange work',function(done) {

        var PAGE_SIZE = 3
        var PAGE = 1
        // create dataSource
        var dataSource = function(query) {
            // check correct page
            query.page
                .should.equal(PAGE)

            // check skip params
            query.skip
                .should.equal((PAGE - 1) * PAGE_SIZE)

            var data = generateMockData({
                type   : 'remote',
                len    : 9,
                request: query
            })

            return new Promise(function(resolve, reject) {
                resolve(data)
            })
        };

        var component = React.createClass({
            displayName : "component",
            increment : function() {
                // increment page size
                PAGE = PAGE + 1
                this.setState({})
            },
            onPageChange : function(page) {
                page.should.equal(3)
                PAGE = page
                this.setState({})
            },
            render: function(){
                return React.createElement("div", null,
                    React.createElement("p", null,
                        React.createElement("button", {
                            className : "incrementBtn",
                            onClick: this.increment
                        }, "Increment")
                    ),
                    DataGrid(
                        {
                            ref: "grid",
                            dataSource: dataSource,
                            page: PAGE,
                            pageSize: PAGE_SIZE,
                            onPageChange: this.onPageChange,
                            idProperty: "id",
                            columns: columns,
                            style: {height: 500}
                        }
                    )
                );
            }
        })

        var componentRendered = render(React.createElement(component,null))

        setTimeout(function() {
            var incrementBtn = findWithClass(componentRendered,'incrementBtn')
            // click increment Button to check controlled page change
            TestUtils.Simulate.click(incrementBtn.getDOMNode())
            setTimeout(function() {
                var nextPageButton = TestUtils.findAllInRenderedTree(componentRendered,function(node) {
                    return node.props.name == PAGINATION_NEXT;
                })[0];
                // click next button to check onPageChange
                TestUtils.Simulate.click(nextPageButton.getDOMNode())
                done()
            },0)
        },0)


    })

})
