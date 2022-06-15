(function ($) {
    "use strict"

    $.fn.modalform = function(options) {
        return this.each(function() {
            const modal = bootstrap.Modal.getOrCreateInstance(this)
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
                    if (typeof value === 'number' || typeof value === 'string') {
                        if ($items.hasClass('tt-input')) {
                            $items.typeahead('val', value);
                        } else {
                            $items.val(value);
                        }
                    }
                }
            });

            $(this).on('shown.bs.modal', function() {
                $(this).find('form').find('input[type!=radio]:visible:enabled, select:visible:enabled, textarea:visible:enabled').first().focus();
            });

            // Handle form validation as per Bootstrap docs
            // https://getbootstrap.com/docs/5.1/forms/validation/#custom-styles
            $(this).find('form.needs-validation').submit(function(event) {
                const $form = $(this);
                event.preventDefault()
                if (this.checkValidity() === false) {
                    event.stopPropagation()
                } else {
                    const data = new FormData(this)
                    const value = Object.fromEntries(data.entries())
                    const action = $form.attr('action')
                    const method = $form.attr('method')

                    $.ajax({
                        headers : {
                            'Accept' : 'application/json',
                            'Content-Type' : 'application/json'
                        },
                        url : action,
                        type : method,
                        data : JSON.stringify(value),
                        success : function(response, textStatus, jqXhr) {
                            modal.hide()
                            if (options.onSuccess != null) {
                                options.onSuccess(response)
                            }
                        },
                        error : function(jqXHR, textStatus, errorThrown) {
                            const response = jqXHR.responseJSON
                            if (options.onError != null) {
                                options.onError(response)
                            }

                            if ('errors' in response) {
                                const errors = response.errors
                                for (const property in errors) {
                                    const $field = $form.find(`#${property}`)
                                    const $feedback = $(`#${property}-feedback`)
                                    $field.one('change', function(event) {
                                        $field[0].setCustomValidity("")
                                        $field.removeClass('is-invalid')
                                        $feedback.text('')
                                    })
                                    $field.addClass('is-invalid')
                                    $field[0].setCustomValidity(errors[property])
                                    $feedback.text(errors[property])
                                }
                            }
                        },
                        complete : function() {
                            if (options.onComplete != null) {
                                options.onComplete()
                            }
                        }
                    })
                }
                $form.addClass('was-validated')
            })

        });
    }

    $(function() {
        $('input[data-role=modalform]').modalform();
    });
}(jQuery));