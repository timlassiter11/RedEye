from wtforms import StringField


class TypeaheadField(StringField):
    def __init__(self, label=None, validators=None, filters=(), description="", 
                    id=None, default=None, widget=None, render_kw=None, name=None, 
                    _form=None, _prefix="", _translations=None, _meta=None):

        if not render_kw:
            render_kw = {}

        render_kw['autocomplete'] = 'off'
        if 'class' in render_kw:
            render_kw['class'] = 'typeahead ' + render_kw['class']
        else:
            render_kw['class'] = 'typeahead'

        super().__init__(label, validators, filters, description, id, default,
                         widget, render_kw, name, _form, _prefix, _translations, _meta)
