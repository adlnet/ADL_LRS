from django import forms
from itertools import chain
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
import pdb

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=200, label='Name')
    email = forms.CharField(max_length=200, label='Email')
    password = forms.CharField(label='Password', 
                                widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(label='Password Again', 
                                widget=forms.PasswordInput(render_value=False))

    def clean(self):
        cleaned = super(RegisterForm, self).clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password2")
        if p1 and p2:
            if p1 == p2:
                return cleaned

        raise forms.ValidationError("Passwords did not match")

SCOPES = (('all', 'all'),
          ('all/read', 'all/read'),
          ('statements/write', 'statements/write'),
          ('statements/read', 'statements/read'),
          ('statements/read/mine', 'statements/read/mine'),
          ('state', 'state'),
          ('define', 'define'),
          ('profile', 'profile'))

class RegClientForm(forms.Form):
    name = forms.CharField(max_length=200, label='Name')
    description = forms.CharField(label='Description', required=False, 
        widget=forms.Textarea())
    scopes = forms.MultipleChoiceField(required=False, initial=[SCOPES[2][0],SCOPES[4][0]],
        widget=forms.CheckboxSelectMultiple, choices=SCOPES)

class MyCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<p class="checkboxes">']
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'<label%s>%s %s</label><br />' % (label_for, rendered_cb, option_label))
        output.append(u'</p>')
        return mark_safe(u'\n'.join(output))

class AuthClientForm(forms.Form):
    scopes = forms.MultipleChoiceField(required=False, initial=SCOPES[0],
        widget=MyCheckboxSelectMultiple(), choices=SCOPES)
    authorize_access = forms.IntegerField(widget=forms.HiddenInput, initial=1)
