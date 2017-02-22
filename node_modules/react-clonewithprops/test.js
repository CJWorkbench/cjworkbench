'use strict';
/*jshint mocha:true  */

var chai = require('chai')
  , scriptjs = require('scriptjs');

var expect = chai.expect;

describe('cloneWithProps in Version 0.9.x', function(){

  beforeEach(function(done){
    scriptjs('http://cdnjs.cloudflare.com/ajax/libs/react/0.9.0/react-with-addons.js', function () {
      done()
    })
  });

  runTests(9)
})

describe('cloneWithProps in Version 0.10.x', function(){

  beforeEach(function(done){
    clearCache()

    scriptjs('http://cdnjs.cloudflare.com/ajax/libs/react/0.10.0/react-with-addons.js', function () {
      done()
    })
  });

  runTests(10)
})

describe('cloneWithProps in Version 0.11.2', function(){

	beforeEach(function(done) {
    clearCache()

    scriptjs('http://cdnjs.cloudflare.com/ajax/libs/react/0.11.2/react-with-addons.js', function () {
      done()
    })
	});

  runTests(11)
})

describe('cloneWithProps in Version 0.12.x', function(){

  beforeEach(function(done){
    clearCache()

    scriptjs('http://cdnjs.cloudflare.com/ajax/libs/react/0.12.0/react-with-addons.js', function () {
      done()
    })
  });

  runTests(12)
})

function runTests(version){
  var React, cloneWithProps, ReactTestUtils;

  it('should be running the correct version of REACT', function() {
    React          = require('react')
    expect(React.version.split('.')[1]).to.equal(''+version)
  })

  // tests taken directly from react's own suite.

  /**
   * Copyright 2013-2014, Facebook, Inc.
   * All rights reserved.
   *
   * This source code is licensed under the BSD-style license found in the
   * LICENSE file in the root directory of this source tree. An additional grant
   * of patent rights can be found in the PATENTS file in the same directory.
   *
   */

  it('should clone a DOM component with new props', function() {
    React          = require('react')
    ReactTestUtils = React.addons.TestUtils
    cloneWithProps = require('./index')

    var Grandparent = React.createClass({
      render: function() {
        return el(Parent, null, el(React.DOM.div, { className: "child" }));
      }
    });

    var Parent = React.createClass({
      render: function() {
        return el(
          React.DOM.div, { className: "parent"},
          cloneWithProps(this.props.children, {className: 'xyz'})
        )
      }
    });

    var component = ReactTestUtils.renderIntoDocument(el(Grandparent));
    expect(component.getDOMNode().childNodes[0].className)
      .to.equal('xyz child');
  });

  it('should clone a composite component with new props', function() {
    React          = require('react')
    ReactTestUtils = React.addons.TestUtils
    cloneWithProps = require('./index')

    var Child = React.createClass({
      render: function() {
        return el(React.DOM.div, { className: this.props.className });
      }
    });

    var Grandparent = React.createClass({
      render: function() {
        return el(Parent, null, 
          el(Child, { className: "child" })
        );
      }
    });

    var Parent = React.createClass({
      render: function() {
        return el(
          React.DOM.div, { className: "parent"},
          cloneWithProps(this.props.children, {className: 'xyz'})
        )
      }
    });

    var component = ReactTestUtils.renderIntoDocument(el(Grandparent));

    expect(component.getDOMNode().childNodes[0].className).to.equal('xyz child');
  });


  it('should transfer the key property', function() {
    React          = require('react')
    ReactTestUtils = React.addons.TestUtils
    cloneWithProps = require('./index')

    var Component = React.createClass({
      render: function() {
        return el(React.DOM.div);
      }
    });

    var clone = cloneWithProps(el(Component), { key: 'xyz' })

    expect(key(clone)).to.equal('xyz');
  });

  it('should transfer children', function() {
    React          = require('react')
    ReactTestUtils = React.addons.TestUtils
    cloneWithProps = require('./index')

    var Component = React.createClass({
      render: function() {
        expect(this.props.children).to.equal('xyz');
        return el(React.DOM.div);
      }
    });

    ReactTestUtils.renderIntoDocument(
      cloneWithProps(el(Component), { children: 'xyz' })
    );
  });


  it('should shallow clone children', function() {
    React          = require('react')
    ReactTestUtils = React.addons.TestUtils
    cloneWithProps = require('./index')

    var Component = React.createClass({
      render: function() {
        expect(this.props.children).to.equal('xyz');
        return el(React.DOM.div);
      }
    });

    ReactTestUtils.renderIntoDocument(
      cloneWithProps(el(Component, null, 'xyz'), {})
    );
  });


  it('should support keys and refs', function() {
    React          = require('react')
    ReactTestUtils = React.addons.TestUtils
    cloneWithProps = require('./index')

    var Component = React.createClass({
      render: function() {
        return el(React.DOM.div)
      }
    });

    var Parent = React.createClass({
      render: function() {
        var clone = cloneWithProps(this.props.children, { key: 'xyz', ref: 'xyz' });

        expect(key(clone)).to.equal('xyz');
        expect(ref(clone)).to.equal('xyz');

        return el(React.DOM.div, null, clone)
      }
    });

    var Grandparent = React.createClass({
      render: function() {
        return el(Parent, null, el(Component, { key: "abc" }))
      }
    });

    ReactTestUtils.renderIntoDocument(el(Grandparent));
  });


  it('should overwrite props', function() {
    React          = require('react')
    ReactTestUtils = React.addons.TestUtils
    cloneWithProps = require('./index')

    var Component = React.createClass({
      render: function() {
        expect(this.props.myprop).to.equal('xyz');
        return el(React.DOM.div);
      }
    });

    ReactTestUtils.renderIntoDocument(
      cloneWithProps(el(Component, { myprop:"abc" }), { myprop: 'xyz'})
    );
  });

  function el(type, props, children){
    if( version <= 11)
      return type(props, children)

    return type.isReactNonLegacyFactory 
      ? window.React.createElement(type.type, props, children) // normalize the DOM.Div
      : window.React.createElement(type, props, children)
  }

  function key(component){
    return version <= 11 ? component.props.key : component.key
  }

  function ref(component){
    return version <= 11 ? component.props.ref : component.ref
  }
}

function clearCache(){
  var reactId = require.resolve('react')
  var cwpId = require.resolve('./index')
  delete require.cache[reactId]
  delete require.cache[cwpId]
}
