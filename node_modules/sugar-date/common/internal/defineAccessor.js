'use strict';

var coreUtilityAliases = require('../var/coreUtilityAliases');

var setProperty = coreUtilityAliases.setProperty;

function defineAccessor(namespace, name, fn) {
  setProperty(namespace, name, fn);
}

module.exports = defineAccessor;