(function () {
    var BootstrapModal = function ($template, options) {
        this.mask = '<{{header|default("h3")}} style="text-align:center;"><i class="{{icon}}"></i>{{text|safe}}</{{header|default("h3")}}>'
        this.$modal = $template.template_render$(options);
    }

    BootstrapModal.prototype.mask_render = function (options) {
        return $.fn.nunjucks_env.renderString(this.mask, options)
    }

    /* Displays a spinner in the body of the modal, indicating that a data load is in progress. */
    BootstrapModal.prototype.loading = function () {
        return this.set_content($(this.mask_render({header: "h1", icon: 'fa-spinner fa-spin fa fa-large'})));
    }

    /* Action retry for fail. */
    BootstrapModal.prototype.retry_action = function (name, callback) {
        xadmin.retry = xadmin.retry || {};
        xadmin.retry[name] = callback;
        return "xadmin.retry['" + name + "']()";
    }

    /* When a data load failure occurs. */
    BootstrapModal.prototype.fail = function (action) {
        return this.set_content(this.mask_render({
            icon: 'fa fa-exclamation-circle text-danger mr-1',
            classes: 'retry',
            header: "h6",
            text: $.fn.nunjucks_env.renderString('<a href="javascript:({{action}})">{{msg}}</a>', {
                msg: gettext("Failed to load data."),
                action: action
            },),
        }));
    }

    BootstrapModal.prototype.find = function (selector) {
        return this.$modal.find(selector)
    }

    /* Change the html in the body of the modal. */
    BootstrapModal.prototype.set_content = function (html) {
        return this.find(".modal-body").html(html);
    }

    BootstrapModal.prototype.show = function () {
        return this.$modal.modal();
    }

    BootstrapModal.prototype.appendTo = function (selector) {
        return this.$modal.appendTo(selector);
    }

    // api to external usage
    xadmin.bs_modal = function(options) {
        return new BootstrapModal($("#nunjucks-modal-main"), options)
    };
})()