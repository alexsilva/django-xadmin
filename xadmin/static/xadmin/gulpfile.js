var gulp = require('gulp');

function genericTask() {
    var srcs = [
        "bower_components/**/css/*.css",
        "bower_components/**/css/*.less",
        "bower_components/**/js/*.js",
        "bower_components/**/dist/*.css",
        "bower_components/**/dist/*.less",
        "bower_components/**/dist/*.js",
        "bower_components/**/locales/*.js",
        "bower_components/**/LICENSE",
        "bower_components/**/img/**",
        "!bower_components/select2/**",
        "!bower_components/popper.js/**",
        "!bower_components/font-awesome/**",
        "!bower_components/nunjucks/**",
        "!bower_components/html5sortable/**",
        "!bower_components/flot/**",
        "!bower_components/datejs/**",
        "!bower_components/bootstrap-datepicker/js/**",
        "!bower_components/selectize/**",
        "!bower_components/sifter/**",
        "!bower_components/bootstrap/**",
        "!bower_components/**/src/**",
        "!bower_components/**/jquery/**",
        "!bower_components/**/jquery.js",
        "!bower_components/**/docs/**",
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor'));
}

function jqueryTask() {
    return gulp.src("bower_components/jquery/dist/**")
        .pipe(gulp.dest('vendor/jquery'));
}

function nunjunksTask() {
    return gulp.src(["bower_components/nunjucks/browser/**/*.js"])
        .pipe(gulp.dest('vendor/nunjucks'));
}


function flotTask() {
    return gulp.src("bower_components/flot/source/*.js")
        .pipe(gulp.dest('vendor/flot/js'));

}

function micropluginTask() {
    return gulp.src("bower_components/microplugin/src/*.js")
        .pipe(gulp.dest('vendor/microplugin/js'));

}

function sifterTask() {
    return gulp.src("bower_components/sifter/*.js")
        .pipe(gulp.dest('vendor/sifter/js'));
}

function selectizeTask() {
    return gulp.src([
        "bower_components/selectize/dist/**/*.js",
        "bower_components/selectize/dist/**/*.css",
        "!bower_components/selectize/dist/lib/**"])
        .pipe(gulp.dest('vendor/selectize'));
}

function select2Task() {
    return gulp.src(["bower_components/select2/dist/**/*.js",
                     "bower_components/select2/dist/**/*.css",
                     "bower_components/select2/dist/**/i18n/*.js",
                     "!bower_components/select2/dist/**/select2.full*"])
        .pipe(gulp.dest('vendor/select2'));
}

function datejsTask() {
    return gulp.src("bower_components/datejs/src/**")
        .pipe(gulp.dest('vendor/datejs/js'));
}

function popperjsTask() {
    return gulp.src("bower_components/popper.js/dist/umd/**")
        .pipe(gulp.dest('vendor/popper'));
}

function jqueryUITask() {
    var srcs = [
        "bower_components/jquery-ui/**/core.js",
        "bower_components/jquery-ui/**/effect.js",
        "bower_components/jquery-ui/**/widget.js",
        "bower_components/jquery-ui/**/**/mouse.js",
        //"bower_components/jquery-ui/**/**/sortable.js",
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor/jquery-ui'));
}

function html5SortableTask() {
    var srcs = [
        "bower_components/html5sortable/dist/html5sortable.js",
        "bower_components/html5sortable/dist/html5sortable.min.js"
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor/html5sortable'));
}

function fontAwesomeTask() {
    var srcs = [
        "bower_components/font-awesome/**/*.js",
        "bower_components/font-awesome/**/*.css",
        "bower_components/font-awesome/**/otfs/**",
        "bower_components/font-awesome/**/webfonts/**",
        "!bower_components/font-awesome/js-packages/**",
        "!bower_components/font-awesome/**/README.md",
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor/font-awesome'));
}

function bootstrapTask() {
    var srcs = [
        "bower_components/bootstrap/dist/**/*.css",
        "bower_components/bootstrap/dist/**/*.js",
        "bower_components/bootstrap/js/dist/**",
        "!bower_components/bootstrap/build/**",
    ];
    return gulp.src(srcs)
        .pipe(gulp.dest('vendor/bootstrap'));
}

exports.select2 = select2Task;
exports.selectize = selectizeTask;
exports.default = gulp.series(
    genericTask,
    jqueryTask,
    popperjsTask,
    nunjunksTask,
    flotTask,
    sifterTask,
    micropluginTask,
    fontAwesomeTask,
    selectizeTask,
    select2Task,
    datejsTask,
    jqueryUITask,
    html5SortableTask,
    bootstrapTask
);
