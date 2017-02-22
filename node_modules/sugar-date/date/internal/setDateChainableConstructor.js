'use strict';

var createDate = require('./createDate'),
    namespaceAliases = require('../../common/var/namespaceAliases'),
    setChainableConstructor = require('../../common/internal/setChainableConstructor');

var sugarDate = namespaceAliases.sugarDate;

function setDateChainableConstructor() {
  setChainableConstructor(sugarDate, createDate);
}

module.exports = setDateChainableConstructor;