'use strict';

var DATE_OPTIONS = require('./DATE_OPTIONS'),
    namespaceAliases = require('../../common/var/namespaceAliases'),
    defineOptionsAccessor = require('../../common/internal/defineOptionsAccessor');

var sugarDate = namespaceAliases.sugarDate;

module.exports = defineOptionsAccessor(sugarDate, DATE_OPTIONS);