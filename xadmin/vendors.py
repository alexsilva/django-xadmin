vendors = {
	"bootstrap": {
		'js': {
			'dev': [
				'xadmin/vendor/popper/popper.js',
				'xadmin/vendor/bootstrap/js/bootstrap.js',
			],
			'production': [
				'xadmin/vendor/popper/popper.min.js',
				'xadmin/vendor/bootstrap/js/bootstrap.min.js',
			],
			'cdn': 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js'
		},
		'css': {
			'dev': [
				'xadmin/vendor/bootstrap/css/bootstrap.css',
			],
			'production': [
				'xadmin/vendor/bootstrap/css/bootstrap.min.css',
			],
			'cdn': 'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css'
		},
	},
	'jquery': {
		"js": {
			'dev': 'xadmin/vendor/jquery/jquery.js',
			'production': 'xadmin/vendor/jquery/jquery.min.js',
		}
	},
	'nunjucks': {
		"js": {
			'dev': ['xadmin/vendor/nunjucks/nunjucks.js',
			        'xadmin/js/nunjucks.engine.js'],
			'production': ['xadmin/vendor/nunjucks/nunjucks.min.js',
			               'xadmin/js/nunjucks.engine.js'],
		}
	},
	'jquery-ui-effect': {
		"js": {
			'dev': 'xadmin/vendor/jquery-ui/ui/effect.js',
			'production': 'xadmin/vendor/jquery-ui/ui/minified/effect.js'
		}
	},
	'jquery-ui-sortable': {
		"js": {
			'dev': [
				'xadmin/vendor/html5sortable/html5sortable.js',
				'xadmin/js/xadmin.plugin.sortable.js',
			],
			'production': [
				'xadmin/vendor/html5sortable/html5sortable.min.js',
				'xadmin/js/xadmin.plugin.sortable.js',
			]
		}
	},
	'datatables': {
		'lang': 'xadmin/vendor/datatables/i18n/%(lang)s.json',
		"js": {
			'dev': ['xadmin/vendor/datatables/datatables.js'],
			'production': ['xadmin/vendor/datatables/datatables.min.js']
		},
		"css": {
			'dev': ['xadmin/vendor/datatables/datatables.css'],
			'production': ['xadmin/vendor/datatables/datatables.min.css']
		}
	},
	"font-awesome": {
		"css": {
			'dev': [
				# fontawesome, brands, regular, solid
				'xadmin/vendor/font-awesome/css/all.css'
			],
			'production': [
				# fontawesome, brands, regular, solid
				'xadmin/vendor/font-awesome/css/all.min.css'
			]
		}
	},
	"timepicker": {
		"css": {
			'dev': 'xadmin/vendor/bootstrap-timepicker/css/timepicker.css',
			'production': 'xadmin/vendor/bootstrap-timepicker/css/timepicker.css',
		},
		"js": {
			'dev': 'xadmin/vendor/bootstrap-timepicker/js/bootstrap-timepicker.js',
			'production': 'xadmin/vendor/bootstrap-timepicker/js/bootstrap-timepicker.js',
		}
	},
	"clockpicker": {
		"css": {
			'dev': 'xadmin/vendor/clockpicker/dist/bootstrap-clockpicker.css',
			'production': 'xadmin/vendor/clockpicker/dist/bootstrap-clockpicker.min.css',
		},
		"js": {
			'dev': 'xadmin/vendor/clockpicker/dist/bootstrap-clockpicker.js',
			'production': 'xadmin/vendor/clockpicker/dist/bootstrap-clockpicker.min.js',
		}
	},
	"datepicker": {
		"css": {
			'dev': 'xadmin/vendor/bootstrap-datepicker/dist/css/bootstrap-datepicker.css'
		},
		"js": {
			'dev': 'xadmin/vendor/bootstrap-datepicker/dist/js/bootstrap-datepicker.js',
			'production': 'xadmin/vendor/bootstrap-datepicker/js/bootstrap-datepicker.min.js',
		}
	},
	"flot": {
		"js": {
			'dev': [
				'xadmin/vendor/flot/js/jquery.canvaswrapper.js',
				'xadmin/vendor/flot/js/jquery.flot.js',
				'xadmin/vendor/flot/js/jquery.flot.drawSeries.js',
				'xadmin/vendor/flot/js/jquery.colorhelpers.js',
				'xadmin/vendor/flot/js/jquery.flot.browser.js',
				'xadmin/vendor/flot/js/jquery.flot.uiConstants.js',
				'xadmin/vendor/flot/js/jquery.flot.saturated.js',
				'xadmin/vendor/flot/js/jquery.flot.pie.js',
				'xadmin/vendor/flot/js/jquery.flot.time.js',
				'xadmin/vendor/flot/js/jquery.flot.resize.js',
				'xadmin/vendor/flot/js/jquery.flot.categories.js']
		}
	},
	"image-gallery": {
		"css": {
			'dev': 'xadmin/vendor/blueimp-gallery/css/blueimp-gallery.css',
			'production': 'xadmin/vendor/blueimp-gallery/css/blueimp-gallery.min.css',
		},
		"js": {
			'dev': ['xadmin/vendor/blueimp-load-image/js/load-image.js',
			        'xadmin/vendor/blueimp-gallery/js/blueimp-gallery.js'],
			'production': ['xadmin/vendor/blueimp-load-image/js/load-image.all.min.js',
			               'xadmin/vendor/blueimp-gallery/js/blueimp-gallery.min.js']
		}
	},
	"select2": {
		"css": {
			'dev': ['xadmin/vendor/select2/css/select2.css'],
			'production': ['xadmin/vendor/select2/css/select2.min.css']
		},
		"js": {
			'dev': [
				'xadmin/vendor/select2/js/select2.js',
				'xadmin/vendor/select2/js/i18n/%(lang)s.js'
			],
			'production': [
				'xadmin/vendor/select2/js/select2.min.js',
				'xadmin/vendor/select2/js/i18n/%(lang)s.js'
			]
		}
	},
	"selectize": {
		"css": {
			'dev': ['xadmin/vendor/selectize/css/selectize.css',
			        'xadmin/vendor/selectize/css/selectize.bootstrap4.css'],
			'production': ['xadmin/vendor/selectize/css/selectize.css',
			               'xadmin/vendor/selectize/css/selectize.bootstrap4.css'],
		},
		"js": {
			'dev': ['xadmin/vendor/selectize/js/selectize.js'],
			'production': ['xadmin/vendor/selectize/js/selectize.min.js']
		}
	},
	"select": {
		"css": {
			'dev': ['xadmin/vendor/select2/css/select2.css',
			        'xadmin/vendor/selectize/css/selectize.css',
			        'xadmin/vendor/selectize/css/selectize.bootstrap4.css'],
			'production': ['xadmin/vendor/select2/css/select2.min.css',
			               'xadmin/vendor/selectize/css/selectize.css',
			               'xadmin/vendor/selectize/css/selectize.bootstrap4.css'],
		},
		"js": {
			'dev': [
				'xadmin/vendor/selectize/js/selectize.js',
				'xadmin/vendor/select2/js/select2.js',
				'xadmin/vendor/select2/js/i18n/%(lang)s.js'],
			'production': [
				'xadmin/vendor/selectize/js/selectize.min.js',
				'xadmin/vendor/select2/js/select2.min.js',
				'xadmin/vendor/select2/js/i18n/%(lang)s.js'
			]
		}
	},
	"multiselect": {
		"css": {
			'dev': 'xadmin/vendor/bootstrap-multiselect/css/bootstrap-multiselect.css',
			'production': 'xadmin/vendor/bootstrap-multiselect/css/bootstrap-multiselect.min.css',
		},
		"js": {
			'dev': 'xadmin/vendor/bootstrap-multiselect/js/bootstrap-multiselect.js',
			'production': 'xadmin/vendor/bootstrap-multiselect/js/bootstrap-multiselect.min.js',
		}
	}
}
