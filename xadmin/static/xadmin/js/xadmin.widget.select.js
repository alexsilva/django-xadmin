;(function($){
    // add select render
    $.fn.exform.renders.push(function(f){
      if($.fn.selectize){
          var getPlaceholder = function ($el) {
                  return $el.hasClass('select-placeholder') && $el.data('placeholder') ? $el.data('placeholder') : null
              },
              selectPlaceholderTemplate = function (data, escape) {
                var label = escape(getPlaceholder(this.$input)),
                    text = escape(data[this.settings.labelField]);
                  return $.fn.nunjucks_env.renderString(
                      '<div class="selectize-field-content" title="{{text}}">' +
                      '<span class="selectize-field-label">{{tabel}}:</span>' +
                      '<span class="selectize-field-text">{{text}}</span>' +
                      '<div>',
                      {label: label, text: text});
              }

          f.find('select:not(.select-search):not(.selectize-off):not([multiple=multiple])').each(function () {
              var $el = $(this),
                  placeholder = getPlaceholder($el),
                  options = {};

              if (placeholder) {
                  options.render = {
                      item: selectPlaceholderTemplate
                  }
              }

              var $select = $el.selectize(options);
              $el.data('selectize', $select[0].selectize);
          });

        f.find('.select-search').each(function(){
            var $el = $(this),
                preload = $el.hasClass('select-preload'),
                placeholder = getPlaceholder($el),
                options = {
                    valueField: 'id',
                    labelField: '__str__',
                    searchField: '__str__',
                    create: false,
                    maxItems: 1,
                    preload: preload,
                    load: function (query, callback) {
                        if (!preload && !query.length) return callback();
                        $.ajax({
                            url: $el.data('search-url') + $el.data('choices'),
                            dataType: 'json',
                            data: {
                                '_q_': query,
                                '_cols': 'id.__str__'
                            },
                            type: 'GET',
                            error: function () {
                                callback();
                            },
                            success: function (res) {
                                var objects = null;
                                if (window.xadmin.object_id) {
                                    var object_id = window.xadmin.object_id;
                                    objects = [];
                                    $.each(res.objects, function (idx, item) {
                                        if (object_id !== item.id) {
                                            objects.push(item);
                                        }
                                    });
                                } else {
                                    objects = res.objects;
                                }
                                callback(objects);
                            }
                        });
                    },
                }

            if (placeholder) {
                options.render = {
                    item: selectPlaceholderTemplate
                }
            }

            var $select = $el.selectize(options);
            $el.data('selectize', $select[0].selectize);
        })

    }});
})(jQuery)
