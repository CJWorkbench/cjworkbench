'use strict';

var DataGrid  = require('../DataGrid')
var React     = require('react/addons')
var TestUtils = React.addons.TestUtils

var TABLE_CLASS         = 'z-table'
var ROW_CLASS           = 'z-row'
var REMOTE_DATA			= 'http://5.101.99.47:8090/10'
var REMOTE_DATA_OPTIONS = '?pageSize=20&page=1&skip=0'

var testUtils = require('../utils')

var render        = testUtils.render
var findWithClass = testUtils.findWithClass
var tryWithClass  = testUtils.tryWithClass
var generateMockData = testUtils.generateMockData

describe('DataGrid Test Suite - DataSource', function(){

	it('check dataSource supported format : array',function(done) {

		var data = generateMockData({type : 'local',len : 1})
        var columns = [
            { name: 'index', title: '#', width: 50 },
            { name: 'firstName'},
            { name: 'lastName'  },
            { name: 'city' },
            { name: 'email' }
        ];

        // table with column menu
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: data,
                columns   : columns
            })
        )

        var rows = tryWithClass(table,ROW_CLASS);
        rows.length.should.equal(1);

        done()

	})

	it('check dataSource supported format : string',function(done) {

		// create mock fetchData

        var fetchData = function(url) {
            url.should.be.equal(REMOTE_DATA + REMOTE_DATA_OPTIONS);
            var data = generateMockData({type : 'remote',len : 1})
            var promise = new Promise(function(resolve,reject) {
                resolve(data);
            })
            return promise;
        }

		var columns = [
            { name: 'index', title: '#', width: 50 },
            { name: 'firstName'},
            { name: 'lastName'  },
            { name: 'city' },
            { name: 'email' }
        ];

        // table with column menu
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: REMOTE_DATA,
                columns   : columns,
                style     : {height:200},
                fetch     : fetchData
            })
        );

        // set time to resolve promise and render table
        setTimeout(function() {
            var rows = tryWithClass(table,ROW_CLASS);
            rows.length.should.equal(1);
            done();
        },0)

	})

	it('check dataSource supported format : function',function(done) {

        // create mock dataSource function

        var dataSource = function() {
            var data = generateMockData({type : 'remote',len : 1})
            var promise = new Promise(function(resolve,reject) {
                resolve(data);
            })
            return promise;
        }

        var columns = [
            { name: 'index', title: '#', width: 50 },
            { name: 'firstName'},
            { name: 'lastName'  },
            { name: 'city' },
            { name: 'email' }
        ];

        // table with column menu
        var table = render(
            DataGrid({
                idProperty: 'id',
                dataSource: dataSource,
                columns   : columns,
                style     : {height:200}
            })
        );

		// set time to resolve promise and render table
        setTimeout(function() {
            var rows = tryWithClass(table,ROW_CLASS);
            rows.length.should.equal(1);
            done();
        },0)
	})

});

