'use strict';

var LocaleHelpers = require('../var/LocaleHelpers'),
    spaceSplit = require('../../common/internal/spaceSplit'),
    fullCompareDate = require('./fullCompareDate'),
    namespaceAliases = require('../../common/var/namespaceAliases'),
    defineInstanceSimilar = require('../../common/internal/defineInstanceSimilar');

var English = LocaleHelpers.English,
    sugarDate = namespaceAliases.sugarDate;

function buildRelativeAliases() {
  var special  = spaceSplit('Today Yesterday Tomorrow Weekday Weekend Future Past');
  var weekdays = English.weekdays.slice(0, 7);
  var months   = English.months.slice(0, 12);
  var together = special.concat(weekdays).concat(months);
  defineInstanceSimilar(sugarDate, together, function(methods, name) {
    methods['is'+ name] = function(d) {
      return fullCompareDate(d, name);
    };
  });
}

module.exports = buildRelativeAliases;