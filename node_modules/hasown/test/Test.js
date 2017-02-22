'use strict'

describe('hasOwn test', function(){

    var hasOwn = require('../index')

    it('should return true for own props', function(){

        hasOwn({name: 'x'}, 'name')
            .should
            .equal(true)

        hasOwn({name: 'x'}, 'name')
            .should
            .equal(true)
    })

    it('should return false for not own props', function(){
        var first = { name: 'x'}
        var second = Object.create(first)

        hasOwn(first, 'name')
            .should
            .equal(true)

        hasOwn(first, 'x')
            .should
            .equal(false)

        hasOwn(second, 'name')
            .should
            .equal(false)

        second.name = 'bil'
        hasOwn(second, 'name')
            .should
            .equal(true)
    })

    it('should allow curry', function(){

        var person = {
            name: 'x'
        }

        var child = Object.create(person)
        child.age = 1
        child.firstName = 'bil'

        var result = []
        var childHasOwn = hasOwn(child)

        for(var k in child) if (childHasOwn(k)){
            result.push(k)
        }

        result
            .should
            .eql(['age','firstName'])
    })
})