(function($) {

    $.fn.actions = function(opts) {
        var self = this
        var options = $.extend({}, $.fn.actions.defaults, opts);
        var actionCheckboxes = $(this).filter(":not(:disabled)");

        updateCounter = function() {
            var sel = $(actionCheckboxes).filter(":checked").length;
            $(options.counterContainer).html(interpolate(
            ngettext('%(sel)s of %(cnt)s selected', '%(sel)s of %(cnt)s selected', sel), {
                sel: sel,
                cnt: _actions_icnt
            }, true));

            if (sel && sel == actionCheckboxes.length) {
                showQuestion();
                $(options.allToggle).prop('checked', true);
            } else {
                clearAcross();
                $(options.allToggle).prop('checked', false);
            }
        }
        var checker = function(e, checked){
            $(this).prop("checked", checked)
                .parentsUntil('.grid-item').parent().toggleClass(options.selectedClass, checked);
            updateCounter();
        }

        lastChecked = null;
        var actionLastChecked = function(event) {
            if (!event) { var event = window.event; }
            var target = event.target ? event.target : event.srcElement;

            if (lastChecked && $.data(lastChecked) != $.data(target) && event.shiftKey == true) {
                var inrange = false;
                $(lastChecked).trigger('checker', target.checked);
                $(actionCheckboxes).each(function() {
                    if ($.data(this) == $.data(lastChecked) || $.data(this) == $.data(target)) {
                        inrange = (inrange) ? false : true;
                    }
                    if (inrange) {
                        $(this).trigger('checker', target.checked);
                    }
                });
            }

            $(target).trigger('checker', target.checked);
            lastChecked = target;
        }
        showQuestion = function() {
            $(options.acrossClears).hide();
            $(options.acrossQuestions).show();
            $(options.allContainer).hide();
        }
        showClear = function() {
            $(options.acrossClears).show();
            $(options.acrossQuestions).hide();
            $(options.allContainer).show();
            $(options.counterContainer).hide();
        }
        reset = function() {
            $(options.acrossClears).hide();
            $(options.acrossQuestions).hide();
            $(options.allContainer).hide();
            $(options.counterContainer).show();
        }
        clearAcross = function() {
            reset();
            $(options.acrossInput).val(0);
        }

        // receiver live inputs
        var $allToggle = $(options.allToggle);
        $allToggle.on("actions_checkbox_add", function (evt, checkbox){
            var $checkbox = $(checkbox);
            if (!$checkbox.data('action.checkbox')) {
                actionCheckboxes = actionCheckboxes.add(checkbox);
                $checkbox.data('action.checkbox', true);
                $checkbox.bind('checker', checker)
                    .click(actionLastChecked);
            }
        // remove old references
        }).on("actions_checkbox_clear", function (evt){
            actionCheckboxes = $(self);

        // receiver action update
        }).on("actions_update_counter", updateCounter);

        // Show counter by default
        $(options.counterContainer).show();
        $(options.allToggle).show().click(function() {
            $(actionCheckboxes).trigger('checker', $(this).is(":checked"));
        });

        $("div.form-actions .question").click(function(event) {
            event.preventDefault();
            $(options.acrossInput).val(1);
            showClear();
        });
        $("div.form-actions .clear").click(function(event) {
            event.preventDefault();
            $(options.allToggle).prop("checked", false);
            $(actionCheckboxes).trigger('checker', false);
            clearAcross();
        });

        $(actionCheckboxes).bind('checker', checker);
        $(actionCheckboxes).click(actionLastChecked);

        // Check state of checkboxes and reinit state if needed
        $(this).filter(":checked").trigger('checker', true);
        updateCounter();
        if ($(options.acrossInput).val() == 1) {
            showClear();
        }
    }
    /* Setup plugin defaults */
    $.fn.actions.defaults = {
        counterContainer: "div.form-actions .action-counter",
        allContainer: "div.form-actions .all",
        acrossInput: "div.form-actions #select-across",
        acrossQuestions: "div.form-actions .question",
        acrossClears: "div.form-actions .clear",
        allToggle: "#action-toggle",
        selectedClass: "warning"
    }

    $.do_action = function(name){
      $('#action').val(name);
      $('#changelist-form').submit();
    }

    $(document).ready(function($) {
        $(".results input.action-select").actions();
        $("a.list-action-menu").click(function (evt){
            evt.preventDefault();
            var name = $(this).data('action-name');
            $('#action').val(name);
            $('#changelist-form').submit();
        })
    });
})(jQuery);
