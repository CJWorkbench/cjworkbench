var gulp = require('gulp');
var filter = require('gulp-filter');
var kclean = require('gulp-kclean');
var modulex = require('gulp-modulex');
var path = require('path');
var rename = require('gulp-rename');
var packageInfo = require('./package.json');
var src = path.resolve(process.cwd(), 'lib');
var build = path.resolve(process.cwd(), 'build');
var clean = require('gulp-clean');
var uglify = require('gulp-uglify');
var jshint = require('gulp-jshint');
var stylish = require('jshint-stylish');
var jscs = require('gulp-jscs');
var replace = require('gulp-replace');
var wrapper = require('gulp-wrapper');
var date = new Date();
var header = ['/*',
        'Copyright ' + date.getFullYear() + ', ' + packageInfo.name + '@' + packageInfo.version,
        packageInfo.license + ' Licensed',
        'build time: ' + (date.toGMTString()),
    '*/', ''].join('\n');
    
gulp.task('lint', function () {
    return gulp.src(['./lib/**/*.js', '!**/parser.js'])
        .pipe(jshint())
        .pipe(jshint.reporter(stylish))
        .pipe(jshint.reporter('fail'))
        .pipe(jscs());
});

gulp.task('clean', function () {
    return gulp.src(build, {
        read: false
    }).pipe(clean());
});

gulp.task('tag',function(done){
    var cp = require('child_process');
    var version = packageInfo.version;
    cp.exec('git tag '+version +' | git push origin '+version+':'+version+' | git push origin master:master',done);
});

gulp.task('standalone', ['build'], function () {
    gulp.src('./build/query-selector-debug.js')
        .pipe(kclean({
            files: [
                {
                    src: './build/query-selector-debug.js',
                    wrap: {
                        start: 'var querySelectorAll = (function(){ var module = {};\n',
                        end: '\nreturn _querySelector_;\n})();'
                    }
                }
            ]
        }))
        .pipe(rename('query-selector-standalone-debug.js'))
        .pipe(replace(/@VERSION@/g, packageInfo.version))
        .pipe(wrapper({
                    header: header
                }))
        .pipe(gulp.dest(build))
        .pipe(filter('query-selector-standalone-debug.js'))
        .pipe(replace(/@DEBUG@/g, ''))
        .pipe(uglify())
        .pipe(rename('query-selector-standalone.js'))
        .pipe(gulp.dest(build));
});

gulp.task('build', ['lint'], function () {
    return gulp.src('./lib/query-selector.js')
        .pipe(modulex({
            modulex: {
                packages: {
                    'query-selector': {
                        base: path.resolve(src, 'query-selector')
                    }
                }
            }
        }))
        .pipe(kclean({
            files: [
                {
                    src: './lib/query-selector-debug.js',
                    outputModule: 'query-selector'
                }
            ]
        }))
        .pipe(replace(/@VERSION@/g, packageInfo.version))
        .pipe(gulp.dest(build))
        .pipe(filter('query-selector-debug.js'))
        .pipe(replace(/@DEBUG@/g, ''))
        .pipe(uglify())
        .pipe(rename('query-selector.js'))
        .pipe(gulp.dest(build));
});

gulp.task('default', ['build', 'standalone']);