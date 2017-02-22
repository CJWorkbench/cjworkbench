'use strict';

var React     = require('react/addons')
var TestUtils = React.addons.TestUtils
var faker = require('faker')

function render(node){
    return TestUtils.renderIntoDocument(node)
}

function findWithClass(root, cls){
    return TestUtils.findRenderedDOMComponentWithClass(root, cls)
}

function tryWithClass(root, cls){
    return TestUtils.scryRenderedDOMComponentsWithClass(root, cls)
}

function generateMockData(options) {
	var data = []
	var i = 0
	for( ;i < options.len; i++ ) {
		data.push({
			id       : i,
			index    : i + 1,
			firstName: faker.name.firstName(),
			lastName : faker.name.lastName(),
			city     : faker.address.city(),
			email    : faker.internet.email()
		})
	}
	if(options.type === 'local') {
		return data
	}

	if(options.type === 'remote') {
		var dataPackage = { count: data.length }
		if(options.request) {
			var startIndex = options.request.skip
			dataPackage.data = data.splice(startIndex,options.request.pageSize)
		} else {
			dataPackage.data = data
		}

		return dataPackage
	}
}

module.exports = {
	render       : render,
	findWithClass: findWithClass,
	tryWithClass : tryWithClass,
	generateMockData : generateMockData
}