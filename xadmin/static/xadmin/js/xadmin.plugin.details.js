(function($){

  var DetailsPop = function(element){
    this.$element = $(element);
    this.res_uri = this.$element.data('res-uri');
    this.edit_uri = this.$element.data('edit-uri');
    this.obj_data = null;

    this.$element.on('click', $.proxy(this.click, this));
  };

  DetailsPop.prototype = {
      constructor: DetailsPop,

      click: function(e){
        e.stopPropagation();
        e.preventDefault();
        var modalId = "detail-modal-id";
        var modal = $('#' + modalId);
        var el = this.$element;
        if(!modal.length) {
          modal = $("#nunjucks-modal-main").template_render$({
            header: {title: el.attr('title')},
            modal: {id: modalId, size: 'modal-lg',},
            confirm_button: {
              text: gettext('Edit'),
              class: "btn-submit edit-btn",
              icon:"fa fa fa-pencil-alt",
              tag: 'a'
            },
          }).appendTo('body');
        }
        modal.find('.modal-title').text(el.attr('title'));
        var edit_btn = modal.find('.edit-btn');
        if(this.edit_uri !== ""){
          edit_btn.attr('href', this.edit_uri);
        }else{
          edit_btn.remove();
        }
        modal.find('.modal-body').html('<h1 style="text-align:center;"><i class="fa-spinner fa-spin fa fa-large"></i></h1>');
        modal.find('.modal-body').load(this.res_uri + '?_format=html', function(response, status, xhr) {
          if (status === "error") {
            var msg = "Sorry but there was an error: ";
            modal.find('.modal-body').html(msg + xhr.status + " " + (typeof xhr === 'string' ? xhr : xhr.responseText || xhr.statusText || 'Unknown error!'));
          }
        });
        modal.modal();
      }
  };

  $.fn.details = function () {
    return this.each(function () {
      var $this = $(this), data = $this.data('details');
      if (!data) {
          $this.data('details', (data = new DetailsPop(this)));
      }
    });
  };

  $(function(){
    $('.details-handler').details();
  });

})(jQuery);


