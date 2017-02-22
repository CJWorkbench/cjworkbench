'use strict';

var Range = require('./internal/Range'),
    rangeIsValid = require('./internal/rangeIsValid'),
    defineOnPrototype = require('../common/internal/defineOnPrototype');

defineOnPrototype(Range, {

  'toString': function() {
    return rangeIsValid(this) ? this.start + '..' + this.end : 'Invalid Range';
  }

});

// This package does not export anything as it is
// simply defining "toString" on Range.prototype.