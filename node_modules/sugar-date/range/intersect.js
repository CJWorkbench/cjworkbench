'use strict';

var Range = require('./internal/Range'),
    defineOnPrototype = require('../common/internal/defineOnPrototype');

defineOnPrototype(Range, {

  'intersect': function(range) {
    if (range.start > this.end || range.end < this.start) {
      return new Range(NaN, NaN);
    }
    return new Range(
      this.start > range.start ? this.start : range.start,
      this.end   < range.end   ? this.end   : range.end
    );
  }

});

// This package does not export anything as it is
// simply defining "intersect" on Range.prototype.