(function ($) {
    "use strict"

    $.fn.apiform = function(options) {
        return this.each(function() {
            const $form = $(this)
            // Handle form validation as per Bootstrap docs
            // https://getbootstrap.com/docs/5.1/forms/validation/#custom-styles

           $form.submit(function(event) {
                event.preventDefault();

                if (options.onSubmit != null) {
                    if (!options.onSubmit(event)) {
                        $form.find(':submit').prop('disabled', false)
                        $form.addClass('was-validated')
                        return;
                    }
                }

                if (this.checkValidity() === false) {
                    event.stopPropagation()
                } else {
                    $form.find(':submit').prop('disabled', true)
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
                            
                            $form.find('input').each(function(index) {
                                this.setCustomValidity('')
                                $(this).removeClass('is-invalid')
                            })

                            if (options.onSuccess != null) {
                                options.onSuccess(response)
                            }
                        },
                        error : function(jqXHR, textStatus, errorThrown) {
                            const response = jqXHR.responseJSON
                            if (options.onError != null) {
                                options.onError(response)
                            }

                            if ('message' in response) {
                                const message = response.message
                                if (typeof message === 'object') {
                                    for (const property in message) {
                                        // Search the entire document for the id first
                                        // This handles cases where the input uses the "form" attribute
                                        // and isn't actually inside the form DOM element.
                                        let $field = $(`#${property}`);
                                        if ($field.length < 1) {
                                            // If that doesn't work search inside the form by the name
                                            $field = $form.find(`[name="${property}"]`);
                                            if ($field.length < 1) {
                                                // TODO: How do we handle when we can't find the bad input?
                                                continue;
                                            }
                                        }

                                        const $feedback = $(`#${property}-feedback`)
                                        $field.one('change', function(event) {
                                            $field[0].setCustomValidity("")
                                            $field.removeClass('is-invalid')
                                            $feedback.text('')
                                        })
                                        $field.addClass('is-invalid')
                                        $field[0].setCustomValidity(message[property])
                                        $feedback.text(message[property])
                                    }
                                } else if (typeof message === "string") {
                                    const alertHtml = `<div class="alert alert-danger alert-dismissible fade show" role="alert">
                                        ${message}
                                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                                    </div>`;
                                    $('#messageContainer').append(alertHtml)
                                }
                            }
                        },
                        complete : function() {
                            $form.find(':submit').prop('disabled', false)
                            $form.addClass('was-validated')
                            if (options.onComplete != null) {
                                options.onComplete()
                            }
                        }
                    })
                }
            })
        });
    }
}(jQuery));