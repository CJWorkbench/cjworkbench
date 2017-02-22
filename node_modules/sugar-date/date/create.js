'use strict';

var Sugar = require('sugar-core'),
    createDate = require('./internal/createDate');

require('./build/setDateChainableConstructorCall');

Sugar.Date.defineStatic({

  'create': function(d, options) {
    return createDate(d, options);
  }

});

module.exports = Sugar.Date.create;