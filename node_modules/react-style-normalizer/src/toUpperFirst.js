'use strict';

module.exports = function(str){
	return str?
			str.charAt(0).toUpperCase() + str.slice(1):
			''
}