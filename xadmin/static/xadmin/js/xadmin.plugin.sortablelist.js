(function($) {
    $(function() {
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                    // Only send the token to relative URLs i.e. locally.
                    xhr.setRequestHeader("X-CSRFToken", $.getCookie('csrftoken'));
                }
            }
        });

        $(".results table tbody").html5sortable({
            items: 'tr',
            cursor: 'move',
            opacity: 0.8,
            itemSerializer: function (serializedItem, sortableContainer){
                var order = $(serializedItem.node).attr("order-key");
                if (order) {
                    var expression = (/(.+)_(.+)/),
                        match = expression.exec(order);
                    if (match) {
                        return {name: match[1], value: match[2]}
                    }
                }
                return {name: 'order', value: serializedItem.index + 1}
            }
        }).each(function() {
            this.addEventListener("sortupdate", function(evt) {
                var $rows = $(this);
                $("#save-order").on("click", function(evt) {
                    var self = $(this),
                        serialize = $rows.html5sortable('serialize'),
                        $btn_icon = $('#save-order-icon', self),
                        btn_icon_default = $btn_icon.attr('class'),
                        btn_icon_icon_loading = self.data('loading-icon'),
                        data = {};
                    serialize.each(function (idx, container){
                        $.each(container.items, function (idx, item){
                            if (!data.hasOwnProperty(item.name)) data[item.name] = [];
                            data[item.name].push(item.value);
                        });
                    });
                    self.addClass('disabled');
                    $btn_icon.removeClass(btn_icon_default).addClass(btn_icon_icon_loading);
                    $.ajax({
                        url: $(this).attr('post-url'),
                        method: 'POST',
                        data: data,
                    }).done(function () {
                        self.removeClass('disabled'); // for safety
                        $btn_icon.removeClass(btn_icon_icon_loading).addClass(btn_icon_default);
                        location.reload(true);
                    }).fail(function () {
                        self.removeClass('disabled');
                        $btn_icon.removeClass(btn_icon_icon_loading).addClass(btn_icon_default);
                    });
                }).show();
            });
        });
    });

})(jQuery);
