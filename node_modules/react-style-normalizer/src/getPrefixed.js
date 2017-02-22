'use strict';

var getStylePrefixed = require('./getStylePrefixed')
var properties       = require('./prefixProps')

module.exports = function(key, value){

	if (!properties[key]){
		return key
	}

	return getStylePrefixed(key, value)
}