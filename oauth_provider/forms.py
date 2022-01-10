from itertools import chain
from django import forms
from django.conf import settings
from django.utils.encoding import force_text
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from .models import Token

SCOPES_LIST = []
for p in settings.OAUTH_SCOPES:
    SCOPES_LIST.append((p[1], p[1]))
FORM_SCOPES = tuple(SCOPES_LIST)


class MyCheckboxSelectMultiple(forms.CheckboxSelectMultiple):

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = ['<p class="checkboxes">']
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = ' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = forms.CheckboxInput(
                final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append('<label%s>%s %s</label><br />' %
                          (label_for, rendered_cb, option_label))
        output.append('</p>')
        return mark_safe('\n'.join(output))


class AuthorizeRequestTokenForm(forms.Form):
    scopes = forms.MultipleChoiceField(required=False, initial=FORM_SCOPES[0],
                                       widget=MyCheckboxSelectMultiple(), choices=FORM_SCOPES)
    authorize_access = forms.IntegerField(widget=forms.HiddenInput, initial=1)
    obj_id = forms.IntegerField(widget=forms.HiddenInput, initial=0)
    oauth_token = forms.CharField(widget=forms.HiddenInput)

    def clean(self):
        cleaned = super(AuthorizeRequestTokenForm, self).clean()
        t = Token.objects.get(id=cleaned.get('obj_id'))
        default_scopes = t.scope.split(' ')
        scopes = cleaned.get('scopes')
        if not scopes:
            raise forms.ValidationError(
                "You need to select permissions for the client")

        if "statements/read/mine" in scopes and "statements/read" in scopes:
            raise forms.ValidationError(
                "'statements/read/mine' and 'statements/read' are conflicting scope values. choose one.")

        # if all is in defaults scopes, any changes must just be limiting scope
        if "all" in default_scopes:
            return cleaned
        elif "all" in scopes:
            # if all wasn't in default_scopes but it's in scopes, error
            raise forms.ValidationError(
                "Can't raise permissions beyond what the consumer registered.")

        # if scope and default aren't the same, see if any scope raises
        # permissions
        if set(scopes) != set(default_scopes):
            # now we know all isn't in default scope and something changed from defaults
            # see if the change is ok
            nomatch = [k for k in scopes if k not in default_scopes]

            if not ("all/read" in nomatch or
                    ("statements/read" in nomatch and "all/read" in default_scopes) or
                    ("statements/read/mine" in nomatch and ("all/read" in default_scopes or "statements/read" in default_scopes))):
                raise forms.ValidationError(
                    "Can't raise permissions beyond what the consumer registered.")

        return cleaned
