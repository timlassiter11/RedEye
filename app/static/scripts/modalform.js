(function ($) {
    "use strict"

    $.fn.modalform = function() {
        return this.each(function() {
            $(this).on('show.bs.modal', function (event) {
                const $element = $(event.relatedTarget);
                if ($element.length === 0) {
                    return;
                }

                const $modal = $(this);
                const $form = $modal.find('form');
                $form.trigger('reset');

                $form.find('input').each(function(index) {
                    this.setCustomValidity('')
                    $(this).removeClass('is-invalid')
                })
    
                const action = $element.data('action');
                const method = $element.data('method');
                const title = $element.data('modal-title');
    
                if (typeof action !== 'undefined') {
                    $form.attr('action', action);
                }
    
                if (typeof method !== 'undefined') {
                    const $methodInput = $form.find('input[name$=method]');
                    if ($methodInput.length > 0) {
                        $methodInput.val(method);
                    } else {
                        $form.attr('method', method);
                    }
                }

                if (typeof title !== 'undefined') {
                    $modal.find('.modal-title').text(title);
                }

                const data = $element.data();
                for (const [key, value] of Object.entries(data)) {
                    const $items = $form.find(`[name$=${key}`).not('[type=radio], [type=checkbox]');
                    if ($items.length > 0) {
                        const type = $items[0].getAttribute('type')
                        if (typeof value === 'number' || typeof value === 'string') {
                            if ($items.hasClass('tt-input')) {
                                $items.typeahead('val', value);
                            } else {
                                $items.val(value);
                            }
                        }
                    }
                }
            });

            $(this).on('shown.bs.modal', function() {
                $(this).find('form').find('input[type!=radio]:visible:enabled, select:visible:enabled, textarea:visible:enabled').first().focus();
            });
        });
    }

    $(function() {
        $('.modal-form').modalform();
    });
}(jQuery));