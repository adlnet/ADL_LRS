from django import forms
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from itertools import chain
from lrs.models import Token

class ValidatorForm(forms.Form):
    jsondata = forms.CharField(label='Data', required=True, 
        widget=forms.Textarea(attrs={'cols':100, 'rows':20}))
    
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
    obj_id = forms.IntegerField(widget=forms.HiddenInput, initial=0)        
    

    def clean(self):
        cleaned = super(AuthClientForm, self).clean()
        t = Token.objects.get(id=cleaned.get('obj_id'))
        default_scopes = t.consumer.default_scopes.split(',')
        scopes = cleaned.get('scopes')
        if not scopes:
            raise forms.ValidationError("you need to select permissions for the client")

        if "statements/read/mine" in scopes and "statements/read" in scopes:
            raise forms.ValidationError("'statements/read/mine' and 'statements/read' are conflicting scope values. choose one.")
        
        # if all is in defaults scopes, any changes must just be limiting scope
        if "all" in default_scopes:
            return cleaned
        elif "all" in scopes: 
            # if all wasn't in default_scopes but it's in scopes, error
            raise forms.ValidationError("Can't raise permissions beyond what the consumer registered.")
        
        # if scope and default aren't the same, see if any scope raises permissions
        if set(scopes) != set(default_scopes):
            # now we know all isn't in default scope and something changed from defaults
            # see if the change is ok
            nomatch = [k for k in scopes if k not in default_scopes]

            if not ("all/read" in nomatch or 
                    ("statements/read" in nomatch and "all/read" in default_scopes) or 
                    ("statements/read/mine" in nomatch and ("all/read" in default_scopes or "statements/read" in default_scopes))):
                raise forms.ValidationError("Can't raise permissions beyond what the consumer registered.")
            
        return cleaned