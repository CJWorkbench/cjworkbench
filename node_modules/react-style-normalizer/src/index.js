'use strict';

var hasOwn      = require('./hasOwn')
var getPrefixed = require('./getPrefixed')

var map      = require('./map')
var plugable = require('./plugable')

function plugins(key, value){

	var result = {
		key  : key,
		value: value
	}

	;(RESULT.plugins || []).forEach(function(fn){

		var tmp = map(function(res){
			return fn(key, value, res)
		}, result)

		if (tmp){
			result = tmp
		}
	})

	return result
}

function normalize(key, value){

	var result = plugins(key, value)

	return map(function(result){
		return {
			key  : getPrefixed(result.key, result.value),
			value: result.value
		}
	}, result)

	return result
}

var RESULT = function(style){

	var k
	var item
	var result = {}

	for (k in style) if (hasOwn(style, k)){
		item = normalize(k, style[k])

		if (!item){
			continue
		}

		map(function(item){
			result[item.key] = item.value
		}, item)
	}

	return result
}

module.exports = plugable(RESULT)