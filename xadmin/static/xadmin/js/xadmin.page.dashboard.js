jQuery(function() {
  $( ".btn-quick-form" ).click(function(){
    var btn = $(this),
        form_url;
    if(btn.is('a')){
      form_url = btn.attr('href');
    }
    if(form_url === undefined){
      form_url = btn.data('form-url');
    }
    if(!btn.data('form-modal')){
      var modal = $("#nunjucks-modal-main").template_render$({
          header: {title: btn.attr('title')},
          confirm_button: {
            text: gettext('Save changes'),
            class: 'btn-submit',
            tag: 'a'
          }
      }).appendTo('body');
      btn.data('form-modal', modal);
      modal.find('.modal-body').load(form_url, function(form_html, status, xhr){
        var form = $(this).find('form');
        form.exform();
        modal.find('.btn-submit').click(function(){
          var csrftoken = $.getCookie('csrftoken');
          //clean form errors
          form.find('.invalid-feedback').remove();
          $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: form.serialize(),
            success: function(data){
              if(data['result'] !== 'success' && data['errors']){
                var err_html, index, non_fields_errors = [];
                for (index = data['errors'].length - 1; index >= 0; index--) {
                  var e = data['errors'][index];
                  var errdiv = form.find('#div_' + e['id']);
                  if(errdiv.length){
                    errdiv.addClass('error');
                    err_html = [];
                    for (var i = e['errors'].length - 1; i >= 0; i--) {
                      err_html.push('<span id="error_'+i+'_'+ e['id'] +'" class="help-inline error"><strong>'+e['errors'][i]+'</strong></span>');
                    }
                    errdiv.find('.controls').append(err_html.join('\n'));
                  } else {
                    non_fields_errors = non_fields_errors.concat(e['errors']);
                  }
                }
                if(non_fields_errors.length){
                  err_html = [];
                  for (index = non_fields_errors.length - 1; index >= 0; index--) {
                    err_html.push('<p class="invalid-feedback"><strong>'+e['errors'][index]+'</strong></p>');
                  }
                  form.prepend(err_html.join('\n'));
                }
              } else {
                btn.trigger('post-success');
              }
            },
            dataType: 'json',
            beforeSend: function(xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
          });
        })
      });
    }
    btn.data('form-modal').modal().css(
        {
            'margin-top': function () {
                return window.pageYOffset;
            }
        });
    return false;
  });

  $('.btn-quick-form').on('post-success', function(e){
    window.location.reload();
  });
});