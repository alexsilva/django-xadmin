
+function ($) { "use strict";

  // POPOVER PUBLIC CLASS DEFINITION
  // ===============================

  var Editpop = function (element, options) {
    this.$element = $(element);
    this.einit('editpop', element, options || {})
  }

  Editpop.Default = $.extend({} , $.fn.popover.Constructor.Default, {
    container: 'body'
  , trigger: 'manual'
  , template: '<div class="popover editpop editable" role="tooltip">' +
          '<div class="arrow"></div><h3 class="popover-header"></h3>' +
          '<div class="popover-body"></div>' +
          '</div>'
  });

  function copyStatic(constructor, staticClass, props) {
      var value;
      for (var index=0; index < props.length; index++) {
          value = Object.getOwnPropertyDescriptor($.fn.popover.Constructor, props[index]);
          Object.defineProperty(constructor, props[index], value);
      }
  }

  copyStatic(Editpop, $.fn.popover.Constructor, [
      "DATA_KEY", "EVENT_KEY", "Event", "DefaultType", "NAME"
  ]);

  // NOTE: POPOVER EXTENDS tooltip.js
  // ================================
  Editpop.prototype = Object.create($.fn.popover.Constructor.prototype);

  Editpop.prototype.constructor = Editpop;

  Editpop.prototype.einit = function (type, element, options) {
    $.fn.popover.Constructor.call(this, element, options);
    this.type = type; // editpop
    this.content = null;
    this.$element.on('click.' + this.type, $.proxy(this.beforeToggle, this));

    this.$text = this.$element.parent().parent().find('.editable-field');
    this.field = this.$element.data('editable-field')
  }

  Editpop.prototype.getDefaults = function () {
    return Editpop.Default;
  }

  Editpop.prototype.beforeToggle = function() {
    var $el = this.$element;

    if(this.content == null){
      var that = this;
      $el.find('>i').removeClass('fa fa-edit').addClass('fa fa-spinner fa-spin');
      $.ajax({
        url: $el.data('editable-loadurl'),
        success: function(content){
          $el.find('>i').removeClass('fa fa-spinner fa-spin').addClass('fa fa-edit');
          that.content = content;
          that.show();
        },
        dataType: 'html'
      })
    } else {
      this.toggle()
    }
  }

  Editpop.prototype.setContent = function () {
    var self = this,
        $tip = $(this.getTipElement()),
        title = this.getTitle();

    $tip.find('.popover-header').html('<button class="close" data-dismiss="editpop">&times;</button>' + title);
    $tip.find('.popover-body').html(this.content);

    var $form = $tip.find('.popover-body > form');

    $form.exform();
    $form.submit($.proxy(this.submit, this));

    this.$form = $form;
    this.$mask = $('<div class="mask"><h2 style="text-align:center;"><i class="fa-spinner fa-spin fa fa-large"></i></h2></div>');
    $tip.find('.popover-body').prepend(this.$mask);

    $tip.removeClass('fade top bottom left right in');

    //bind events
    $tip.find('[data-dismiss=editpop]').on('click.' + this.type, function (evt) {
      self.hide();
    });

    //var me = ((Math.random() * 10) + "").replace(/\D/g, '');
    //var click_event_ns = "click." + me + " touchstart." + me;
    var that = this;

    // $('body').on(click_event_ns, function(e) {
    //   if ( !$tip.has(e.target).length ) { that.hide() }
    // })

    $(document).on('keyup.editpop', function(e) {
      if (e.keyCode === 27) { that.hide(); }
    });
  }

  Editpop.prototype.hasContent = function () {
    return this.getTitle() || this.content;
  }

  Editpop.prototype.submit = function(e) {
      e.stopPropagation();
      e.preventDefault();
      
      $.when(this.save())
      .done($.proxy(function(data) {
        this.$mask.hide();
        this.$form.find(".is-invalid." + this.type).removeClass("is-invalid"); // remove error class
        this.$form.find(".invalid-feedback." + this.type).remove(); // remove old errors
        if(data['result'] !== 'success' && data['errors']){
          var err_id, $input;
          for (var i = data['errors'].length - 1; i >= 0; i--) {
            var e = data['errors'][i];
            $input = this.$form.find("#" + e['id']).addClass('is-invalid');
            for (var j = e['errors'].length - 1; j >= 0; j--) {
              err_id = "div_" + e['id'] + j;
              $input.after($.fn.nunjucks_env.renderString(
                '<div class="{{err_cls}} invalid-feedback" id="{{id}}">{{message}}</div>',
                {message: e['errors'][j], id: err_id, err_cls: this.type}
              ));
            }
          }
        } else {
          this.$text.html(data['new_html'][this.field]);
          this.hide();
        }
      }, this))
      .fail($.proxy(function(xhr) {
        this.$mask.hide();
        this.$mask.parents('.popover').hide();
        alert(typeof xhr === 'string' ? xhr : xhr.responseText || xhr.statusText || 'Unknown error!');
      }, this))
  }

  Editpop.prototype.save = function(newValue) {
    this.$form.find('.controls .help-block.error').remove();

    this.$mask.show();

    var off_check_box = Object();
    this.$form.find('input[type=checkbox]').each(function(){
      if(!$(this).is(':checked')){
        off_check_box[$(this).attr('name')] = ''
      }
    });

    return $.ajax({
      data: [this.$form.serialize(), $.param(off_check_box)].join('&'),
      url: this.$form.attr('action'),
      type: "POST",
      dataType: 'json',
      beforeSend: function(xhr, settings) {
          xhr.setRequestHeader("X-CSRFToken", $.getCookie('csrftoken'))
      }
    })
  }

  // POPOVER PLUGIN DEFINITION
  // =========================

  var old = $.fn.editpop;

  $.fn.editpop = function (option) {
    return this.each(function () {
      var $this   = $(this);
      var data    = $this.data('bs.editpop');
      var options = typeof option == 'object' && options;

      if (!data) $this.data('bs.editpop', (data = new Editpop(this, options)));
      if (typeof option == 'string') data[option]();
    })
  }

  $.fn.editpop.Constructor = Editpop;


  // POPOVER NO CONFLICT
  // ===================

  $.fn.editpop.noConflict = function () {
    $.fn.editpop = old;
    return this
  }

  $(function(){
    $('.editable-handler').editpop();
  })

}(window.jQuery);
