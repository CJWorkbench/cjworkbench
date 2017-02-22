var gulp = require('gulp');
var plugins = require('gulp-load-plugins')();

gulp.task('build', function() {
  return gulp.src('src/**/*.js')
    .pipe(plugins.babel())
    .pipe(gulp.dest('dist'));
});