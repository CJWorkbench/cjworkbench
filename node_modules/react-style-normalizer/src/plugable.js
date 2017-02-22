'use strict';

var getCssPrefixedValue = require('./getCssPrefixedValue')

module.exports = function(target){
	target.plugins = target.plugins || [
		(function(){
			var values = {
				'flex':1,
				'inline-flex':1
			}

			return function(key, value){
				if (key === 'display' && value in values){
					return {
						key  : key,
						value: getCssPrefixedValue(key, value, true)
					}
				}
			}
		})()
	]

	target.plugin = function(fn){
		target.plugins = target.plugins || []

		target.plugins.push(fn)
	}

	return target
}