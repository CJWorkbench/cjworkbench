'use strict';

var methodDefineAliases = require('../var/methodDefineAliases'),
    collectSimilarMethods = require('./collectSimilarMethods');

var defineInstance = methodDefineAliases.defineInstance;

function defineInstanceSimilar(sugarNamespace, set, fn, flags) {
  defineInstance(sugarNamespace, collectSimilarMethods(set, fn), flags);
}

module.exports = defineInstanceSimilar;